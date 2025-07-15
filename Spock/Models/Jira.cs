using System.Text.Json.Serialization;

namespace Spock.Models;

public record JiraResult : SearchResult
{
    public JiraIssue? Content { get; init; }
}

public record JiraIssue
{
    public required Project Project { get; init; }
    public required IssueType IssueType { get; init; }
    public User? Assignee { get; init; }
    public required Status Status { get; init; }
    public List<Component>? Components { get; init; }
    public string[]? Tags { get; init; }
}

public record IssueType
{
    public required string Name { get; init; }
    public Uri? IconUrl { get; init; }
}

public record User
{
    public required string DisplayName { get; init; }
    public required string Name { get; init; }
}

public record Status
{
    public required string Name { get; init; }
}

public record Component
{
    public required string Name { get; init; }
}

public record Project
{
    public required string Key { get; init; }
    public required AvatarUrls AvatarUrls { get; init; }
}

public record AvatarUrls
{
    [JsonPropertyName("16x16")]
    public required Uri Small { get; init; }
}