# us-states-codepipeline2

AWS Lambda関数のサンプルと、それをCI/CDでデプロイするCodePipeline構成一式。

## 構成

- `src/app.py` — サンプルLambda関数（Python 3.13）。`GET /hello?name=xxx` で挨拶を返すAPI。
- `tests/test_app.py` — Lambda関数のユニットテスト（pytest）。
- `src/Dockerfile` — Lambda用コンテナイメージの定義（ベース: `public.ecr.aws/lambda/python:3.13`）。
- `template.yaml` — AWS SAM（CloudFormation）テンプレート。コンテナイメージ型（`PackageType: Image`）のLambda関数とHTTP API (API Gateway) を定義。
- `buildspec.yml` — CodeBuild用のビルド定義。テスト実行後、`sam build`（docker build）/ `sam package`（ECRへpush）を行う。

## パイプライン構成

```
GitHub (main)
   │  CodeStarConnections (Webhook)
   ▼
[Source] ── CodePipeline
   │
   ▼
[Build]  CodeBuild (特権モード / Docker)
   - pytest でユニットテスト実行
   - sam build で src/Dockerfile からコンテナイメージをビルド
   - sam package でイメージを ECR (us-states-lambda-pipeline) へpush
   - ImageUri を埋め込んだ packaged.yaml を出力アーティファクトとして渡す
   │
   ▼
[Approval] 手動承認
   │
   ▼
[Deploy] CloudFormation (CREATE_UPDATE)
   - packaged.yaml を使ってスタック `us-states-lambda-sample-stack` を作成/更新
   - Lambda関数（ECRのイメージを参照）+ API Gatewayがデプロイされる
```

AWS上のリソース名は `us-states-lambda-pipeline-*` のプレフィックスで統一。
（同一AWSアカウント内に存在する `us-states-codepipeline2-*` という名前の別プロジェクト用リソース（EC2/CodeDeployの本番パイプライン）とは無関係で、干渉しない。）

## デプロイされるスタックの出力

- `HelloFunctionArn` — Lambda関数のARN
- `HelloApiUrl` — 動作確認用のHTTPSエンドポイント

詳しい構築手順・作成したAWSリソース一覧・ハマったポイントは
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) を参照。

## ローカルでのテスト

```bash
pip install -r requirements.txt
pytest tests/ -v
```
