# C# Code Style (.NET 10 / C# 14)

## Critical Rules

> **This rule applies ONLY to .NET 10+ projects.** Check the `.csproj` for `<TargetFramework>net10.0</TargetFramework>` or higher.

The `.editorconfig` enforces these patterns. Violations will show as warnings/errors.

| Pattern | Use This | NOT This |
|---------|----------|----------|
| File-scoped namespaces | `namespace Foo;` | `namespace Foo { }` |
| Null checks | `is not null` | `!= null` |
| Null coalescing | `??`, `??=`, `?.` | Manual null checks |
| var usage | `var x = new Foo()` | `Foo x = new Foo()` |

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Types | PascalCase | `UserService`, `OrderProcessor` |
| Methods | PascalCase | `GetUser()`, `ProcessOrder()` |
| Interfaces | `I` prefix + PascalCase | `IUserRepository`, `ILogger` |
| Private fields | `_camelCase` | `_userService`, `_logger` |
| Parameters | camelCase | `userId`, `orderDate` |
| Constants | PascalCase | `MaxRetryCount`, `DefaultTimeout` |

---

## Common Patterns

See: [code/style-csharp/patterns.md](code/style-csharp/patterns.md)

### File-Scoped Namespaces

Use `namespace Foo;` instead of `namespace Foo { }` to save indentation.

### Pattern Matching for Null Checks

Use `is not null` and `is null` instead of `!= null` and `== null`.

### Null Coalescing Operators

Use `??`, `??=`, and `?.` for concise null handling.

### Expression Bodies

Use for simple, single-expression members only.

### var Usage

Use `var` when the type is apparent from the right-hand side.

---

## Primary Constructors (C# 12+)

For simple dependency injection, prefer primary constructors.

---

## Collection Expressions (C# 12+)

Use `[1, 2, 3]` syntax instead of `new int[] { 1, 2, 3 }`.

---

## Record Types

Use records for immutable data transfer objects.

---

## Async/Await Patterns

- Use `Async` suffix on async methods
- Include `CancellationToken` parameter
- Use `ConfigureAwait(false)` in library code
- Never block on async with `.Result` or `.Wait()`

---

## Common Mistakes to Avoid

1. Using `namespace Foo { }` instead of `namespace Foo;`
2. Using `!= null` instead of `is not null`
3. Blocking on async with `.Result` or `.Wait()`
4. Missing `CancellationToken` in async methods
5. Using `var` when type isn't obvious from context
6. Creating mutable DTOs instead of records
7. Missing `readonly` on struct fields that don't change
