namespace Spock.Models;

public record FileResult : SearchResult
{
    public int SizeBytes { get; init; }
}