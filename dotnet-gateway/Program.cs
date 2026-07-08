using MarketPulse.Gateway.Services;
using Microsoft.Extensions.Caching.Memory;
using QuestPDF.Infrastructure;
using OfficeOpenXml;
using Serilog;

// ── License declarations ───────────────────────────────────────────────────────
QuestPDF.Settings.License = LicenseType.Community;
ExcelPackage.LicenseContext = LicenseContext.NonCommercial;

// ── Serilog ────────────────────────────────────────────────────────────────────
Log.Logger = new LoggerConfiguration()
    .WriteTo.Console(outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}")
    .WriteTo.File("logs/gateway-.log", rollingInterval: RollingInterval.Day)
    .CreateLogger();

var builder = WebApplication.CreateBuilder(args);
builder.Host.UseSerilog();

// ── Services ──────────────────────────────────────────────────────────────────
builder.Services.AddControllers();
builder.Services.AddMemoryCache();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new()
    {
        Title       = "MarketPulse Enterprise Gateway",
        Version     = "v1",
        Description = "C# ASP.NET Core 8 API Gateway — Rolls-Royce MTU Power Systems use case. " +
                      "Proxies to the Python/LangGraph backend and adds MRO scheduling, " +
                      "equipment health monitoring, and Excel/PDF report generation."
    });
});

// HttpClient for Python backend
builder.Services.AddHttpClient("PythonBackend", client =>
{
    var url = builder.Configuration["PythonBackendUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(url);
    client.Timeout     = TimeSpan.FromSeconds(60);
    client.DefaultRequestHeaders.Add("X-Gateway", "DotNet-MarketPulse");
});

// Application Insights (no-op when connection string is empty)
var appInsightsConn = builder.Configuration["ApplicationInsights:ConnectionString"];
if (!string.IsNullOrWhiteSpace(appInsightsConn))
    builder.Services.AddApplicationInsightsTelemetry(o => o.ConnectionString = appInsightsConn);

// CORS — allow React dev server and future Vercel domain
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins("http://localhost:5173", "http://localhost:3000", "https://*.vercel.app")
     .AllowAnyHeader()
     .AllowAnyMethod()
     .AllowCredentials()));

// Domain services
builder.Services.AddSingleton<PythonBackendService>();
builder.Services.AddSingleton<MaintenanceService>();
builder.Services.AddSingleton<EquipmentHealthService>();
builder.Services.AddScoped<AzureStorageService>();
builder.Services.AddScoped<ReportService>();

// ── App pipeline ──────────────────────────────────────────────────────────────
var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "MarketPulse Gateway v1");
    c.RoutePrefix = "swagger";
    c.DocumentTitle = "MarketPulse Enterprise API";
});

app.UseSerilogRequestLogging();
app.UseCors();
app.UseRouting();
app.MapControllers();

// Health endpoint
app.MapGet("/health", () => new
{
    status    = "healthy",
    service   = "MarketPulse Enterprise Gateway",
    version   = "1.0.0",
    timestamp = DateTime.UtcNow.ToString("O"),
    backend   = builder.Configuration["PythonBackendUrl"]
});

Log.Information("=== MarketPulse Enterprise Gateway ===");
Log.Information("Swagger UI  : http://localhost:5000/swagger");
Log.Information("Python back : {Url}", builder.Configuration["PythonBackendUrl"]);
Log.Information("======================================");

app.Run();
