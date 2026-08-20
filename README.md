# Amazon Promo Bot

**FastAPI · affiliate workflow automation · product validation · safe-by-design integrations**

Backend prototype for managing a curated catalog of Amazon products, validating ASINs, generating affiliate links and preparing reusable promotional messages.

The current version is intentionally conservative: it does **not** scrape Amazon, does not automate browser sessions and does not invent prices or promotions. Live pricing is designed to depend on an official Amazon API integration when credentials and access are available.

## What the project demonstrates

- API design with **FastAPI**;
- structured persistence with **SQLAlchemy + SQLite**;
- product/ASIN validation workflows;
- affiliate-link generation;
- dashboard and export endpoints;
- configuration through environment variables;
- automated tests with **pytest**;
- explicit separation between verified data and unavailable external data;
- defensive integration design for future third-party APIs.

## Project

The implementation lives in [`amazon-promo-bot/`](amazon-promo-bot/).

Full setup instructions, endpoints, architecture notes and current limitations are documented in the project's [technical README](amazon-promo-bot/README.md).

## Current status

The repository represents a **working V1 for manual product management and affiliate-link workflows**. Real-time prices and verified discounts are deliberately disabled until an official Amazon integration is configured.
