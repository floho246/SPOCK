using System.Net.Http.Json;
using System.Text.Json;
using Spock.Models;

namespace Spock.Service;

internal sealed class SpockApiService(HttpClient httpClient)
{
    private readonly JsonSerializerOptions _options = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<HealthResponse?> GetHealthAsync()
    {
        var response = await httpClient.GetAsync("/api/health");
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<HealthResponse>(_options);
    }

    public async Task<SourcesResponse?> GetSourcesAsync()
    {
        var response = await httpClient.GetAsync("/api/sources");
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<SourcesResponse>(_options);
    }

    public async Task<SearchResponse?> SearchAsync(SearchRequest request, CancellationToken cancellationToken = default)
    {
        var response = await httpClient.PostAsJsonAsync("/api/search", request, cancellationToken);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<SearchResponse>(_options, cancellationToken);
    }
}