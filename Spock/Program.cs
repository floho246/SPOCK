using System.ClientModel;
using System.Net.Http.Json;
using Blazored.SessionStorage;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using Microsoft.Extensions.AI;
using OpenAI;
using OpenAI.Chat;
using Spock;
using Spock.Models;
using Spock.Service;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

// Config aus config.json laden. Nicht vorhanden -> Absturz.
using var http = new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
};
// Versionsnummer um die config aus dem Cache zu busten
using var versionJson = await http.GetAsync($"generated/version.json?ts={DateTimeOffset.UtcNow.ToUnixTimeSeconds()}");
var version = await versionJson.Content.ReadFromJsonAsync<VersionInfo>();
using var response = await http.GetAsync($"config.json?v={version?.Revision ?? ""}");
var config = await response.Content.ReadFromJsonAsync<Dictionary<string, string>>();
var apiUrl = config?["ApiBaseUrl"];
var llmUrl = config?["LLMUrl"];

builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

builder.Services.AddBlazoredSessionStorage(sessionStorageOptions =>
{
    sessionStorageOptions.JsonSerializerOptions.PropertyNameCaseInsensitive = true;
});
builder.Services.AddScoped(_ => new HttpClient { BaseAddress = new Uri(builder.HostEnvironment.BaseAddress) })
    .AddHttpClient<SpockApiService>(client =>
    {
        client.BaseAddress = new Uri(apiUrl!);
        client.Timeout = TimeSpan.FromSeconds(200); // lange llm-anfragen
    });
builder.Services.AddHttpClient<LlmService>(client => { client.BaseAddress = new Uri(llmUrl!); });

// Versionsservice für Link im Footer
builder.Services.AddSingleton(async _ =>
{
    using var httpClient = new HttpClient();
    httpClient.BaseAddress = new Uri(builder.HostEnvironment.BaseAddress);
    var json = await httpClient.GetAsync($"generated/version.json?ts={DateTimeOffset.UtcNow.ToUnixTimeSeconds()}");
    return await json.Content.ReadFromJsonAsync<VersionInfo>();
});

ChatClient client = new(
    model: "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf",
    credential: new ApiKeyCredential("123"), // kein ApiKey nötig
    options: new OpenAIClientOptions
    {
        Endpoint = new Uri(llmUrl!)
    }
);
builder.Services.AddChatClient(client.AsIChatClient());

// DevExpress
builder.Services.AddDevExpressBlazor();
builder.Services.AddDevExpressAI();

await builder.Build().RunAsync();