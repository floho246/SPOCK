using Spock.Util;

namespace Spock.Models;

public class FilterItem<T>
{
    public required T Value { get; init; }
    public int Count { get; init; }
}

public class FilterModel
{
    public DateOnly? Start { get; set; }
    public DateOnly? End { get; set; }
    public IEnumerable<string> SelectedNames { get; set; } = [];
    public IEnumerable<string> SelectedSources { get; set; } = [];

    public bool Match(SearchResult res)
    {
        var sourceMatch = !SelectedSources.Any() || SelectedSources.Contains(res.GetNameForSourceType());
        // Filter an? Name vorhanden und entspricht Filter?
        var nameMatch = !SelectedNames.Any() ||
                        (!string.IsNullOrWhiteSpace(res.Creator) && SelectedNames.Contains(res.Creator));
        var dateMatch = res.Created is null && Start is null && End is null ||
                        res.Created is { } dt && dt >= (Start ?? DateOnly.MinValue) && dt <= (End ?? DateOnly.MaxValue);

        // alle Filter müssen passen
        return sourceMatch && nameMatch && dateMatch;
    }
}

public record VersionInfo
{
    public string? Revision { get; init; }
    public Uri? Uri { get; init; }
}