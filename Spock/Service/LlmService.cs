using System.Net.Http.Json;
using System.Text.Json;
using Spock.Models;

namespace Spock.Service;

internal sealed class LlmService(HttpClient httpClient)
{
    private readonly JsonSerializerOptions _options = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<ModelResponse?> GetModelsAsync()
    {
        var response = await httpClient.GetAsync("models");
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<ModelResponse>(_options);
    }
}