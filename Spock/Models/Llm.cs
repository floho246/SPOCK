using System.Text.Json.Serialization;

namespace Spock.Models;

public record ModelResponse
{
    [JsonPropertyName("object")]
    public required string ObjectType { get; init; }

    [JsonPropertyName("data")]
    public required IEnumerable<ModelData> Data { get; init; }
}

public record ModelData
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("object")]
    public required string ObjectType { get; init; }

    [JsonPropertyName("owned_by")]
    public required string OwnedBy { get; init; }

    [JsonPropertyName("permissions")]
    public required IEnumerable<object> Permissions { get; init; }
}
