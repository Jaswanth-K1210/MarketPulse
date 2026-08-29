namespace MarketPulse.Gateway.Services;

/// <summary>
/// Uploads generated reports to Azure Blob Storage.
/// Falls back to local /tmp/reports/ when the connection string is not configured,
/// so the service works in dev without any Azure credentials.
/// </summary>
public class AzureStorageService
{
    private readonly IConfiguration _config;
    private readonly ILogger<AzureStorageService> _log;
    private const string Container = "marketpulse-reports";

    public AzureStorageService(IConfiguration config, ILogger<AzureStorageService> log)
    {
        _config = config;
        _log    = log;
    }

    public async Task<string> UploadReportAsync(
        byte[] fileBytes,
        string fileName,
        CancellationToken ct = default)
    {
        var connStr = _config["AzureStorageConnectionString"] ?? string.Empty;

        if (string.IsNullOrWhiteSpace(connStr))
            return await SaveLocalAsync(fileBytes, fileName, ct);

        try
        {
            var Azure = Azure_StorageBlobsClient(connStr, fileName, fileBytes);
            _log.LogInformation("Report uploaded to Azure Blob: {Container}/{File}", Container, fileName);
            return Azure;
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "Azure upload failed, falling back to local storage");
            return await SaveLocalAsync(fileBytes, fileName, ct);
        }
    }

    // Lazy-load the Azure SDK so the service compiles without Azure creds configured
    private string Azure_StorageBlobsClient(string connStr, string fileName, byte[] data)
    {
        var blobServiceClient = new Azure.Storage.Blobs.BlobServiceClient(connStr);
        var containerClient   = blobServiceClient.GetBlobContainerClient(Container);
        containerClient.CreateIfNotExists();
        var blobClient = containerClient.GetBlobClient(fileName);
        using var stream = new MemoryStream(data);
        blobClient.Upload(stream, overwrite: true);
        return blobClient.Uri.ToString();
    }

    private async Task<string> SaveLocalAsync(byte[] fileBytes, string fileName, CancellationToken ct)
    {
        var dir  = Path.Combine(Path.GetTempPath(), "marketpulse-reports");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, fileName);
        await File.WriteAllBytesAsync(path, fileBytes, ct);
        _log.LogInformation("Report saved locally: {Path}", path);
        return $"file://{path}";
    }
}
