# Role-Based Access Control

## Role definitions

### Admin

- Can access authenticated endpoints.
- Can perform Admin-only actions.
- Can manage all users and departments in future APIs.
- Can access department-scoped and unscoped resources by default policy.

### Manager

- Can access authenticated endpoints.
- Can use Manager-or-Admin guarded endpoints.
- Can access resources in their own department only.
- Can manage Staff users in their own department by policy.
- Cannot manage Admin or Manager users.
- Cannot access unscoped resources by default department policy.

### Staff

- Can access authenticated endpoints.
- Can access resources in their own department only.
- Cannot manage users.
- Cannot assign roles.
- Cannot access unscoped resources by default department policy.

## Dependency guards

- `get_current_user`: requires a valid Bearer access token, decodes it, loads the User from PostgreSQL, checks that the User exists and is active, then returns the User ORM instance.
- `require_roles`: generic dependency factory for explicitly allowed roles.
- `require_admin`: allows only `UserRole.ADMIN`.
- `require_manager_or_admin`: allows `UserRole.ADMIN` and `UserRole.MANAGER`.

`require_roles()` with no allowed roles is invalid and raises `ValueError` when the dependency is created.

## Department policy

Implemented in `app.core.permissions.can_access_department`.

- Admin can access every Department.
- Admin can access resources with `department_id = NULL`.
- Manager can access only resources whose `department_id` matches the Manager's own `department_id`.
- Staff can access only resources whose `department_id` matches the Staff user's own `department_id`.
- Manager or Staff users without a Department have no department-scoped access.
- Resources with `department_id = NULL` are allowed only for Admin by the default policy.

## Department user management policy

Implemented in `app.core.permissions.can_manage_department_users`.

- Admin can manage users for any Department, including an unscoped target Department.
- Manager can manage users only for the Manager's own Department.
- Manager without a Department cannot manage Department users.
- Manager cannot manage an unscoped target Department.
- Staff cannot manage Department users.

## User management policy

Implemented in `app.core.permissions.can_manage_user`.

- Admin can manage every User.
- Manager can manage only Staff users in the same Department.
- Manager cannot manage Admin users.
- Manager cannot manage other Manager users.
- Manager cannot manage users in another Department.
- Manager cannot manage users without a Department.
- Manager without a Department cannot manage users.
- Staff cannot manage users.

The policy checks the target User's current role. Validation of a requested new role belongs to the role assignment policy and future User APIs.

## Role assignment

Implemented in `app.core.permissions.can_assign_role`.

- Admin can assign `ADMIN`, `MANAGER`, and `STAFF`.
- Manager can assign only `STAFF`.
- Staff cannot assign any role.

## Authorization source

Database User record is the source of truth.

Authorization must use the User ORM instance loaded from PostgreSQL by `get_current_user`. Access tokens are used to identify the user through `sub`; they are not the final source for role, department, or active-status authorization decisions.

Roles must not be trusted from request body, query parameters, headers, or JWT role claims. RBAC uses explicit allowed role sets; it does not use numeric role hierarchy or string ordering.
## TASK-007 User and Department APIs

Implemented API access rules:

- User list, create, update, and deactivate are Admin-only.
- User detail is available to Admin or to the same authenticated User.
- Manager and Staff reading another User receive `404 RESOURCE_NOT_FOUND` to avoid account enumeration.
- Department list, create, detail, update, and delete are Admin-only.
- Manager same-Department policies from TASK-006 are not applied to User or Department CRUD in TASK-007; they remain available for future business resources.
- Missing or invalid Bearer tokens return `401`.
- Authenticated users with the wrong role on Admin endpoints return `403 FORBIDDEN`.
- Truly missing resources return `404 RESOURCE_NOT_FOUND`.


## TASK-008 Document access data model

The database model now supports these future document access concepts:

- `PRIVATE` scope.
- `DEPARTMENT` scope.
- `ORGANIZATION` scope.
- Direct User grants.
- Direct Department grants.
- `VIEW` permission.
- `EDIT` permission.
- `MANAGE` permission.

Planned access semantics:

- `PRIVATE`: Admin, uploader, direct User grants, and direct Department grants.
- `DEPARTMENT`: Admin, users in `documents.department_id`, direct User grants, and direct Department grants.
- `ORGANIZATION`: every authenticated active User; direct grants may still exist but are usually not needed for `VIEW`.
- Direct grants supplement access granted by scope; they do not deny or reduce existing access.
- Admin implicit permission is not stored in `document_permissions`.
- Uploader ownership is stored in `documents.uploaded_by`, not as an automatic permission row.

Not implemented yet:

- `can_view_document`.
- `can_edit_document`.
- `can_manage_document`.
- Accessible-document query filter.
- Document API authorization.
- Permission hierarchy mapping for `VIEW < EDIT < MANAGE`.

The database User record and Department remain the source of authorization truth.
## TASK-010 Document access-control implementation

Document view policy is implemented with shared pure policy helpers and a reusable PostgreSQL filter:

- Admin can view every non-deleted Document.
- `ORGANIZATION` Documents are visible to every active authenticated User.
- `DEPARTMENT` Documents are visible to Users whose current database `department_id` matches `documents.department_id`.
- Uploaders have implicit view access through `documents.uploaded_by`.
- Direct User grants with `VIEW`, `EDIT`, or `MANAGE` allow view access.
- Direct Department grants with `VIEW`, `EDIT`, or `MANAGE` allow view access for Users in that Department.

Document edit policy:

- Admin can edit every non-deleted Document.
- Manager can edit a Document they uploaded.
- Manager can edit a Department-scoped Document in their own Department.
- Manager can edit with direct User or Department `EDIT` or `MANAGE` grant.
- Staff cannot edit Documents in MVP, even with direct `EDIT` or `MANAGE` grants.

Document manage/delete policy:

- Admin can manage every non-deleted Document.
- Manager can manage a Document they uploaded.
- Manager can manage a Department-scoped Document in their own Department.
- Manager can manage with direct User or Department `MANAGE` grant.
- Staff cannot manage or delete Documents in MVP.

Direct permission management is Admin-only. Permission levels are evaluated through explicit sets for view, edit, and manage; enum string ordering and numeric hierarchy are not used.

The reusable accessible-document filter is applied in PostgreSQL for list, detail, status, and download. JWTs are not trusted for role or Department authorization; `get_current_user` reloads the User from PostgreSQL for each request.