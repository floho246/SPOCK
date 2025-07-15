using System.Text.Json.Serialization;

namespace Spock.Models;

[JsonConverter(typeof(JsonStringEnumConverter))]
public enum SearchType
{
    Keyword,
    Embedding,
    Hybrid
}

public class SearchRequest
{
    public required string Query { get; set; }
    public required IEnumerable<string> Sources { get; set; }
    public required SearchType SearchType { get; set; }
    public int? TopK { get; set; } = 10;
    public bool EnableGenerative { get; set; }
    public string? PromptExtension { get; set; }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "sourceType", IgnoreUnrecognizedTypeDiscriminators = true)]
[JsonDerivedType(typeof(JiraResult), "Jira")]
[JsonDerivedType(typeof(WikiResult), "Confluence")]
[JsonDerivedType(typeof(FileResult), "Network Drive")]
public record SearchResult
{
    public required string Id { get; init; }
    public required string BrowseUrl { get; init; }
    public string? Title { get; init; }
    public string? Summary { get; init; }
    public DateOnly? Created { get; init; }
    public string? Creator { get; init; }
    public float Score { get; init; }
}

public record SearchResponse
{
    public required IEnumerable<SearchResult> Results { get; init; }
    public string? Answer { get; init; }
}

public record SourceInfo
{
    public required string Name { get; init; }

    public required string Type { get; init; }

    public bool Available { get; init; }

    public bool Embeddings { get; init; }
}

public class SourcesResponse
{
    public List<SourceInfo> Sources { get; set; }
}

public record HealthResponse
{
    public required string Status { get; init; }
}