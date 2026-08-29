using Microsoft.AspNetCore.Mvc;
using MarketPulse.Gateway.Models;
using MarketPulse.Gateway.Services;

namespace MarketPulse.Gateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReportsController : ControllerBase
{
    private readonly ReportService _reports;
    private readonly ILogger<ReportsController> _log;

    public ReportsController(ReportService reports, ILogger<ReportsController> log)
    {
        _reports = reports;
        _log     = log;
    }

    /// <summary>Generate an Excel or PDF intelligence report and return a download URL.</summary>
    [HttpPost("generate")]
    [ProducesResponseType(typeof(ReportResult), 200)]
    [ProducesResponseType(400)]
    [ProducesResponseType(500)]
    public async Task<IActionResult> Generate([FromBody] ReportRequest req, CancellationToken ct)
    {
        var type = req.ReportType?.ToLower();
        if (type is not ("excel" or "pdf"))
            return BadRequest(new { error = "ReportType must be 'excel' or 'pdf'." });

        if (string.IsNullOrWhiteSpace(req.Title))
            req.Title = $"MarketPulse Intelligence Report — {DateTime.UtcNow:yyyy-MM-dd}";

        try
        {
            var result = await _reports.GenerateReportAsync(req, ct);
            _log.LogInformation("Report {Id} generated ({Type}, {Bytes:N0} bytes)",
                result.ReportId, result.ReportType, result.FileSizeBytes);
            return Ok(result);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Report generation failed");
            return StatusCode(500, new { error = "Report generation failed.", detail = ex.Message });
        }
    }

    /// <summary>Download a locally-stored report by filename (dev-mode only).</summary>
    [HttpGet("download/{fileName}")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult Download(string fileName)
    {
        // Sanitise: only allow alphanumeric + dash + dot to prevent path traversal
        if (!System.Text.RegularExpressions.Regex.IsMatch(fileName, @"^[\w\-]+\.(xlsx|pdf)$"))
            return BadRequest(new { error = "Invalid filename." });

        var path = Path.Combine(Path.GetTempPath(), "marketpulse-reports", fileName);
        if (!System.IO.File.Exists(path))
            return NotFound(new { error = $"Report {fileName} not found." });

        var mime = fileName.EndsWith(".pdf")
            ? "application/pdf"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

        return PhysicalFile(path, mime, fileName);
    }
}
