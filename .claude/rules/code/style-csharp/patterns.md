# C# Code Patterns

## File-Scoped Namespaces

```csharp
// Correct
namespace MyApp.Services;

public class UserService { }
```

```csharp
// Wrong - wastes indentation
namespace MyApp.Services
{
    public class UserService { }
}
```

## Pattern Matching for Null Checks

```csharp
// Correct
if (user is not null) { }
if (user is null) { }

// Wrong
if (user != null) { }
if (user == null) { }
```

## Null Coalescing Operators

```csharp
// Correct - null coalescing
var name = user?.Name ?? "Unknown";
_cache ??= new Dictionary<string, object>();

// Wrong - verbose null checks
var name = user != null ? user.Name : "Unknown";
if (_cache == null) _cache = new Dictionary<string, object>();
```

## Expression Bodies

```csharp
// Correct - expression body for simple members
public string FullName => $"{FirstName} {LastName}";
public int Count => _items.Count;
public override string ToString() => $"User: {Name}";

// Wrong for complex logic - use block body instead
public string FullName
{
    get
    {
        if (string.IsNullOrEmpty(LastName))
            return FirstName;
        return $"{FirstName} {LastName}";
    }
}
```

## var Usage

```csharp
// Correct - type is obvious
var user = new User();
var users = new List<User>();
var name = user.GetFullName();  // Return type clear from method name

// Correct - explicit type when not obvious
User user = GetEntity();  // Return type not clear
int count = CalculateTotal();  // Clarifies the type
```

## Primary Constructors (C# 12+)

```csharp
// Correct - primary constructor
public class UserService(ILogger<UserService> logger, IUserRepository repo)
{
    public User GetUser(int id) => repo.GetById(id);
}

// Also acceptable - traditional constructor for complex initialization
public class UserService
{
    private readonly ILogger<UserService> _logger;
    private readonly IUserRepository _repo;

    public UserService(ILogger<UserService> logger, IUserRepository repo)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        _repo = repo ?? throw new ArgumentNullException(nameof(repo));
    }
}
```

## Collection Expressions (C# 12+)

```csharp
// Correct - collection expressions
int[] numbers = [1, 2, 3, 4, 5];
List<string> names = ["Alice", "Bob", "Charlie"];
Dictionary<string, int> ages = new() { ["Alice"] = 30, ["Bob"] = 25 };

// Wrong - verbose initialization
int[] numbers = new int[] { 1, 2, 3, 4, 5 };
List<string> names = new List<string> { "Alice", "Bob", "Charlie" };
```

## Record Types

```csharp
// Correct - record for DTOs
public record UserDto(int Id, string Name, string Email);
public record CreateUserRequest(string Name, string Email);

// Correct - record struct for small value types
public readonly record struct Point(int X, int Y);

// Use class for entities with identity and behavior
public class User
{
    public int Id { get; private set; }
    public string Name { get; set; }
    public void UpdateEmail(string email) { /* validation */ }
}
```

## Async/Await Patterns

```csharp
// Correct - async suffix, CancellationToken support
public async Task<User> GetUserAsync(int id, CancellationToken ct = default)
{
    return await _repo.GetByIdAsync(id, ct);
}

// Correct - ConfigureAwait(false) in library code
public async Task<User> GetUserAsync(int id)
{
    return await _repo.GetByIdAsync(id).ConfigureAwait(false);
}

// Wrong - blocking on async
public User GetUser(int id)
{
    return _repo.GetByIdAsync(id).Result;  // Deadlock risk!
}
```
