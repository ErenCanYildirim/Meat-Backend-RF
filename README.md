# Meat-Backend-RF
Refactored Backend

Authentication + Authorization (role-based middleware)
Database layer: SQLite (dev) -> PostgreSQL with migrations 
File storage: local (later cloud)

Database:

Users table with roles
orders: 
roles/permissions
analytics cache: pre-computed metrics

analytics service:
-> standalone service 
-> scheduled jobs
-> metrics storage
-> dashboard API 

security:
-> RBAC middleware
-> input validation 
-> rate limiting 
-> env. configuration

RBAC:
    - admin, manager, customer
    - granular permissions
    - middleware (route-level protection)
    - scalable

service layer pattern:
    - separation of concerns: API routes handle HTTP requests, services handle business logic
    - testability

DB strategy:
    - single database
    - connection pooling

Notes to self:
    - always use __init__.py in every directory you want to import from
    - start imports from root package (app.etc)
    - run app from root dir 
    - use absolute imports 