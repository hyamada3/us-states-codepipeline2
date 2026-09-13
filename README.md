# us-states-codepipeline2

AWS Lambda関数のサンプルと、それをCI/CDでデプロイするCodePipeline構成一式。

## 構成

- `src/app.py` — サンプルLambda関数（Python 3.13）。`GET /hello?name=xxx` で挨拶を返すAPI。
- `tests/test_app.py` — Lambda関数のユニットテスト（pytest）。
- `template.yaml` — AWS SAM（CloudFormation）テンプレート。Lambda関数とHTTP API (API Gateway) を定義。
- `buildspec.yml` — CodeBuild用のビルド定義。テスト実行後、`sam build` / `sam package` を行う。

## パイプライン構成

```
GitHub (main)
   │  CodeStarConnections
   ▼
[Source] ── CodePipeline
   │
   ▼
[Build]  CodeBuild
   - pytest でユニットテスト実行
   - sam build / sam package でLambdaをパッケージ化しS3へアップロード
   - packaged.yaml を出力アーティファクトとして渡す
   │
   ▼
[Deploy] CloudFormation (CREATE_UPDATE)
   - packaged.yaml を使ってスタック `us-states-lambda-sample-stack` を作成/更新
   - Lambda関数 + API Gatewayがデプロイされる
```

AWS上のリソース名は `us-states-lambda-pipeline-*` のプレフィックスで統一。
（同一AWSアカウント内に存在する `us-states-codepipeline2-*` という名前の別プロジェクト用リソース（EC2/CodeDeployの本番パイプライン）とは無関係で、干渉しない。）

## デプロイされるスタックの出力

- `HelloFunctionArn` — Lambda関数のARN
- `HelloApiUrl` — 動作確認用のHTTPSエンドポイント

## ローカルでのテスト

```bash
pip install -r requirements.txt
pytest tests/ -v
```
