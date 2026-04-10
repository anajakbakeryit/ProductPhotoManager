# Coding Standards

## Naming Conventions
- **Frontend**: camelCase (vars/fns), PascalCase (components/types)
- **Backend**: snake_case (Python vars/fns), PascalCase (classes/models)
- **Files**: kebab-case (frontend), snake_case (backend)
- **Constants**: SCREAMING_SNAKE_CASE

## Formatting
- **Frontend**: Prettier (Metronic default config)
- **Backend**: ruff (Python linter/formatter)

## Imports
- **Frontend**: `@/` alias → `frontend/src/`
- **Backend**: `backend.api.` prefix for internal, `core.` / `utils.` for shared

## ค้นหาก่อนสร้าง
- ค้นหา existing components, hooks, routers ก่อนสร้างใหม่เสมอ
- Reuse code ที่มีอยู่แทนการ duplicate

## Language
- **UI text**: ภาษาไทย (user-facing)
- **Code**: ภาษาอังกฤษ (variable names, function names, comments)

## Git
- Commit messages: descriptive, English
- ห้าม commit `.env`, credentials, `node_modules`, `__pycache__`
