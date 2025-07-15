using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.WebUtilities;
using Spock.Models;
using Blazored.SessionStorage;

namespace Spock.Pages;

public class SearchQueryPage : ComponentBase
{
    private const string QueryParamQuery = "q";
    private const string QueryParamSources = "s";
    private const string QueryParamSearchType = "t";
    private const string QueryParamTopK = "k";
    private const string QueryParamEnableGenerative = "g";
    private const string QueryParamPromptExtension = "p";

    [Inject] protected ISessionStorageService SessionStorage { get; set; } = null!;
    [Inject] protected NavigationManager Navigation { get; set; } = null!;

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamQuery)]
    public string? Query { get; set; }

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamSources)]
    public string? Sources { get; set; }

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamSearchType)]
    public string? SearchTypeRaw { get; set; }

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamTopK)]
    public int? TopK { get; set; }

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamEnableGenerative)]
    public bool? EnableGenerative { get; set; }

    [Parameter]
    [SupplyParameterFromQuery(Name = QueryParamPromptExtension)]
    public string? PromptExtension { get; set; }

    protected SearchRequest SearchRequest = null!;

    protected bool HasValidQueryParams;

    protected override void OnInitialized()
    {
        base.OnInitialized();

        // 1️⃣ Standardwerte setzen
        SearchRequest = new SearchRequest { Query = "", Sources = [], SearchType = SearchType.Hybrid };
    }

    protected override async Task OnParametersSetAsync()
    {
        await base.OnParametersSetAsync();

        // 2️⃣ Session Storage checken
        if (await SessionStorage.GetItemAsync<SearchRequest>("SearchRequest") is { } searchRequest)
        {
            SearchRequest = searchRequest;
        }

        HasValidQueryParams = false;
        // 3️⃣ Query Params sind am wichtigsten
        if (!string.IsNullOrWhiteSpace(Query))
        {
            SearchRequest.Query = Query;
            HasValidQueryParams = true;
        }

        if (!string.IsNullOrWhiteSpace(Sources))
        {
            SearchRequest.Sources = Sources.Split(',', StringSplitOptions.RemoveEmptyEntries);
            HasValidQueryParams = true;
        }

        if (Enum.TryParse<SearchType>(SearchTypeRaw, ignoreCase: true, out var parsed))
        {
            SearchRequest.SearchType = parsed;
            HasValidQueryParams = true;
        }

        if (TopK.HasValue)
        {
            SearchRequest.TopK = TopK.Value;
            HasValidQueryParams = true;
        }

        if (EnableGenerative.HasValue)
        {
            SearchRequest.EnableGenerative = EnableGenerative.Value;
            HasValidQueryParams = true;
        }

        if (!string.IsNullOrWhiteSpace(PromptExtension))
        {
            SearchRequest.PromptExtension = PromptExtension;
            HasValidQueryParams = true;
        }
    }

    protected void UpdateUrlFromSearchRequest()
    {
        var queryParams = new Dictionary<string, string?>
        {
            [QueryParamQuery] = SearchRequest.Query,
            [QueryParamSources] = string.Join(",", SearchRequest.Sources),
            [QueryParamSearchType] = SearchRequest.SearchType.ToString()
        };

        if (SearchRequest.TopK != 10) queryParams[QueryParamTopK] = SearchRequest.TopK.ToString();

        if (SearchRequest.EnableGenerative)
            queryParams[QueryParamEnableGenerative] = SearchRequest.EnableGenerative.ToString();

        if (!string.IsNullOrWhiteSpace(SearchRequest.PromptExtension))
            queryParams[QueryParamPromptExtension] = SearchRequest.PromptExtension;

        var uri = new Uri(Navigation.Uri);
        var baseUrl = uri.GetLeftPart(UriPartial.Path);
        var newUri = QueryHelpers.AddQueryString(baseUrl, queryParams);

        Navigation.NavigateTo(newUri, forceLoad: false);
    }
}