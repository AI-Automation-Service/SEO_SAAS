# Product Requirements Document (PRD)

## Overview

SEO OS is an internal platform for managing SEO across multiple client websites. It is not a SaaS product. It is a private CLI tool run by one operator to serve their clients.

## Problem Statement

Managing SEO for multiple clients requires repeating the same analysis, strategy, and content workflows for each website. Without a unified system, work is manual, inconsistent, and hard to scale.

## Solution

A modular, config-driven SEO operating system where:
- Every client is a self-contained project directory
- All agents are reusable across projects
- All skills are stateless and reusable
- Configuration drives behavior — no hardcoded business logic

## Users

- **Primary operator:** The SEO professional running this tool (single user)
- **Beneficiaries:** Client businesses whose websites are managed

## Non-Goals

- This is NOT a multi-tenant SaaS platform
- No user authentication or billing
- No web UI (CLI only for now)
- No real-time dashboard

## Core Requirements

### Must Have (Phase 1–4)
- Project configuration system (project.yaml per client)
- Knowledge base per project
- Skill loading system (claude-seo integration)
- Integration layer (WordPress, GSC, GA4)

### Should Have (Phase 5–7)
- Technical SEO agent
- SEO strategy agent
- Monitoring agent

### Future (Phase 8–10)
- Content engine API
- Automation / scheduler
- Complete documentation
