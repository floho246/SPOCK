using System.Drawing;
using Spock.Models;

namespace Spock.Util;

internal static class Styles
{
    internal static string GetIconClassForSourceType(this SearchResult searchResult)
    {
        return searchResult switch
        {
            JiraResult => "fab fa-jira",
            WikiResult => "fab fa-confluence",
            FileResult => "fas fa-file-alt",
            _ => "far fa-book"
        };
    }

    public static string GetNameForSourceType(this SearchResult searchResult)
    {
        // könnte auch explizit sein
        return searchResult.GetType().Name switch
        {
            nameof(SearchResult) => "Unbekannt",
            nameof(FileResult) => "Datei",
            _ => searchResult.GetType().Name.Replace("Result", "")
        };
    }

    internal static string GetColor(float score, float minScore, float maxScore, Color minColor, Color maxColor)
    {
        if (maxScore == minScore)
            return $"rgb({maxColor.R}, {maxColor.G}, {maxColor.B})";

        var normalized = (score - minScore) / (maxScore - minScore);

        var r = (int)(minColor.R + (maxColor.R - minColor.R) * normalized);
        var g = (int)(minColor.G + (maxColor.G - minColor.G) * normalized);
        var b = (int)(minColor.B + (maxColor.B - minColor.B) * normalized);

        return $"rgb({r},{g},{b})";
    }
}