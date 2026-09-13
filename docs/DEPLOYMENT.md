# デプロイ構成ドキュメント

Lambda関数サンプルをGitHub→CodePipeline→CodeBuild→CloudFormationで
自動デプロイする構成を構築した際の記録。

作成日: 2026-09-13 / リージョン: ap-northeast-1 / AWSアカウント: 277731792740

## 全体構成

```
GitHub (hyamada3/us-states-codepipeline2, main)
   │  Webhook (CodeStarConnections)
   ▼
CodePipeline: us-states-lambda-pipeline
   │
   ├─ [Source] AppSource
   │     CodeStarSourceConnection でリポジトリのコードを取得
   │
   ├─ [Build] BuildAndPackage (CodeBuild)
   │     1. pip install -r requirements.txt
   │     2. pytest tests/ -v            … ユニットテスト
   │     3. sam build                    … Lambdaパッケージのビルド
   │     4. sam package --s3-bucket ...  … S3へアップロードし packaged.yaml を生成
   │
   ├─ [Approval] ManualApproval
   │     デプロイ前に手動承認が必要(AWSコンソールのCodePipeline画面、
   │     または `aws codepipeline put-approval-result` で承認/却下する)
   │
   └─ [Deploy] DeployLambdaStack (CloudFormation, CREATE_UPDATE)
         packaged.yaml を使って us-states-lambda-sample-stack を作成/更新
         → Lambda関数 (us-states-lambda-sample) + HTTP API (API Gateway) を作成
```

## 作成したAWSリソース一覧

| 種別 | 名前 | 用途 |
|---|---|---|
| S3バケット | `us-states-lambda-pipeline-artifacts-277731792740` | CodePipelineのアーティファクト保管、SAMパッケージのアップロード先 |
| IAMロール | `us-states-lambda-pipeline-codepipeline-role` | CodePipeline本体の実行ロール |
| IAMロール | `us-states-lambda-pipeline-codebuild-role` | CodeBuildの実行ロール(ログ出力・S3アクセス) |
| IAMロール | `us-states-lambda-pipeline-cfn-deploy-role` | CloudFormationがスタックリソースを作成する際に引き受けるロール |
| CodeBuildプロジェクト | `us-states-lambda-pipeline-build` | テスト実行 + `sam build`/`sam package` |
| CodePipeline | `us-states-lambda-pipeline` | Source→Build→Deployの3ステージパイプライン |
| CloudFormationスタック | `us-states-lambda-sample-stack` | パイプラインのDeployステージが作成。Lambda関数とHTTP APIを含む |
| Lambda関数 | `us-states-lambda-sample` | サンプル関数本体(Python 3.13) |
| API Gateway (HTTP API) | (スタックが自動命名) | `GET /hello` を `us-states-lambda-sample` にプロキシ |

GitHub連携には既存のCodeStarConnection(`github-connection1`,
`arn:aws:codeconnections:ap-northeast-1:277731792740:connection/edf7aac9-8b48-4dc0-9eed-e510bc34cdcb`)
を再利用した(読み取り専用のSourceアクションのみで使用するため、他プロジェクトとの共有は問題ない)。

### 命名について

同一AWSアカウント内に、別プロジェクト(タイポ入りリポジトリ`hyamada3/us-states-codepipline2`、
EC2+CodeDeployで`us-state-app2`をデプロイする本番パイプライン)向けに
`us-states-codepipeline2-*`という名前のリソース(S3バケット・IAMロール・パイプライン)が
既に稼働中だった。名前が酷似しており誤って上書きするリスクがあったため、
今回の新規リソースはすべて `us-states-lambda-pipeline-*` というプレフィックスで統一し、
既存リソースには一切変更を加えていない。

## デプロイ結果の確認

```
$ curl https://wuexmyrprc.execute-api.ap-northeast-1.amazonaws.com/hello
{"message": "Hello, World!", "path": "/hello"}

$ curl "https://wuexmyrprc.execute-api.ap-northeast-1.amazonaws.com/hello?name=Yamada"
{"message": "Hello, Yamada!", "path": "/hello"}
```

## ハマったポイント

構築時にCodeBuild/CloudFormationのデプロイが3回失敗した。原因と対処は以下の通り。

### 1. `sam build --use-container=false` が無効なオプション指定だった

最新のAWS SAM CLIでは `--use-container` は値を取らないブールフラグであり、
`=false` を付けるとCLIがエラーで終了する(`Error: Option '--use-container' does not value.`)。
デフォルトでコンテナを使わないビルドになるため、`buildspec.yml` を単に `sam build` に修正した。

### 2. SAMの`Transform`処理に `cloudformation:CreateChangeSet` 権限が不足

`template.yaml` は `Transform: AWS::Serverless-2016-10-31` を使用しており、
CloudFormationはスタック作成時に内部でこのTransform(マクロ)に対して
`cloudformation:CreateChangeSet` を実行する。デプロイロール
(`us-states-lambda-pipeline-cfn-deploy-role`)にこの権限がなく、
`AccessDenied`でスタックがロールバックした。
`arn:aws:cloudformation:ap-northeast-1:aws:transform/Serverless-2016-10-31`
に対する `cloudformation:CreateChangeSet` を許可するステートメントを追加して解消。

### 3. API Gatewayのタグ付けAPIに対する権限ARNパターンが狭すぎた

HTTP API (`AWS::ApiGatewayV2::Api`) 作成時、CloudFormationはリソース作成後に
`apigateway:POST` でタグを付与するが、そのAPIコールのリソースARNは
`arn:aws:apigateway:<region>::/tags/arn%3Aaws%3Aapigateway%3A...%2Fv2%2Fapis%2F*`
という形式になる。ポリシーを `arn:aws:apigateway:<region>::/apis*` に限定していたため
マッチせず`AccessDeniedException`が発生した。API Gatewayのリソース単位ARNは
API種別ごとに形式がばらつくため、リージョン内の全APIGatewayリソースを対象にした
`arn:aws:apigateway:<region>::/*` に広げて解消した。

## 今後の変更方法

`main`ブランチにpushすると、Webhook経由で自動的にパイプラインが起動する
(Source→Build→Deploy)。Lambdaのコードを変更する場合は `src/app.py` を、
インフラ構成(タイムアウト、メモリ、追加のAPIルートなど)を変更する場合は
`template.yaml` を編集してpushすればよい。
