using System.Text.Json;
using MarketPulse.Gateway.Models;
using OfficeOpenXml;
using OfficeOpenXml.Style;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using DrawColor = System.Drawing.Color;

namespace MarketPulse.Gateway.Services;

/// <summary>
/// Generates Excel (EPPlus) and PDF (QuestPDF) intelligence reports
/// combining live alert data from the Python backend with MTU fleet health.
/// </summary>
public class ReportService
{
    private readonly PythonBackendService _backend;
    private readonly AzureStorageService  _storage;
    private readonly MaintenanceService   _maint;
    private readonly EquipmentHealthService _health;
    private readonly ILogger<ReportService> _log;

    private static readonly JsonSerializerOptions _json = new() { PropertyNameCaseInsensitive = true };

    public ReportService(
        PythonBackendService    backend,
        AzureStorageService     storage,
        MaintenanceService      maint,
        EquipmentHealthService  health,
        ILogger<ReportService>  log)
    {
        _backend = backend;
        _storage = storage;
        _maint   = maint;
        _health  = health;
        _log     = log;
    }

    public async Task<ReportResult> GenerateReportAsync(ReportRequest req, CancellationToken ct = default)
    {
        _log.LogInformation("Generating {Type} report: {Title}", req.ReportType, req.Title);

        // Fetch live alerts from Python backend
        List<AlertDto> alerts = new();
        if (req.IncludeAlerts)
        {
            try
            {
                var raw = await _backend.GetAlertsAsync(ct: ct);
                var doc = JsonDocument.Parse(raw);
                if (doc.RootElement.TryGetProperty("alerts", out var arr))
                    alerts = JsonSerializer.Deserialize<List<AlertDto>>(arr.GetRawText(), _json) ?? new();
            }
            catch (Exception ex)
            {
                _log.LogWarning(ex, "Could not fetch alerts — report will use empty alerts list");
            }
        }

        var fleet  = _health.GetFleetSummary();
        var sched  = _maint.GetAll();
        var reportId   = $"RPT-{DateTime.UtcNow:yyyyMMddHHmmss}";
        var ext        = req.ReportType.ToLower() == "pdf" ? "pdf" : "xlsx";
        var fileName   = $"{reportId}.{ext}";

        byte[] bytes = req.ReportType.ToLower() == "pdf"
            ? GeneratePdf(req, alerts, fleet, sched, reportId)
            : GenerateExcel(req, alerts, fleet, sched, reportId);

        var url = await _storage.UploadReportAsync(bytes, fileName, ct);

        return new ReportResult
        {
            ReportId      = reportId,
            DownloadUrl   = url,
            FileName      = fileName,
            ReportType    = req.ReportType,
            FileSizeBytes = bytes.Length,
            GeneratedAt   = DateTime.UtcNow,
            Status        = "ready"
        };
    }

    // ── Excel ────────────────────────────────────────────────────────────────

    private byte[] GenerateExcel(
        ReportRequest req,
        List<AlertDto> alerts,
        FleetHealthSummary fleet,
        IReadOnlyList<MaintenanceSchedule> sched,
        string reportId)
    {
        using var pkg = new ExcelPackage();

        // ── Sheet 1: Alert Summary ─────────────────────────────────────────
        var ws1 = pkg.Workbook.Worksheets.Add("Alert Summary");
        ws1.Cells["A1"].Value = req.Title;
        ws1.Cells["A1:F1"].Merge = true;
        ws1.Cells["A1"].Style.Font.Bold  = true;
        ws1.Cells["A1"].Style.Font.Size  = 14;
        ws1.Cells["A1"].Style.Fill.PatternType = ExcelFillStyle.Solid;
        ws1.Cells["A1"].Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x1e, 0x3a, 0x8a));
        ws1.Cells["A1"].Style.Font.Color.SetColor(DrawColor.White);

        ws1.Cells["A2"].Value = $"Generated: {DateTime.UtcNow:yyyy-MM-dd HH:mm} UTC  |  Report ID: {reportId}";
        ws1.Cells["A2:F2"].Merge = true;
        ws1.Cells["A2"].Style.Font.Italic = true;

        var headers1 = new[] { "Ticker", "Severity", "Impact %", "Confidence", "Description", "Timestamp" };
        for (int i = 0; i < headers1.Length; i++)
        {
            var cell = ws1.Cells[4, i + 1];
            cell.Value = headers1[i];
            cell.Style.Font.Bold = true;
            cell.Style.Fill.PatternType = ExcelFillStyle.Solid;
            cell.Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x1e, 0x40, 0xaf));
            cell.Style.Font.Color.SetColor(DrawColor.White);
        }

        for (int r = 0; r < alerts.Count; r++)
        {
            var a = alerts[r];
            ws1.Cells[r + 5, 1].Value = a.Ticker;
            ws1.Cells[r + 5, 2].Value = a.Severity.ToUpper();
            ws1.Cells[r + 5, 3].Value = Math.Round(a.ImpactPercent, 2);
            ws1.Cells[r + 5, 4].Value = Math.Round(a.Confidence, 2);
            ws1.Cells[r + 5, 5].Value = a.Description[..Math.Min(a.Description.Length, 120)];
            ws1.Cells[r + 5, 6].Value = a.Timestamp;

            // Colour-code severity
            var sevCell = ws1.Cells[r + 5, 2];
            sevCell.Style.Fill.PatternType = ExcelFillStyle.Solid;
            sevCell.Style.Fill.BackgroundColor.SetColor(a.Severity.ToUpper() switch
            {
                "HIGH"     => DrawColor.FromArgb(0xfe, 0xe2, 0xe2),
                "CRITICAL" => DrawColor.FromArgb(0xef, 0x44, 0x44),
                "MEDIUM"   => DrawColor.FromArgb(0xff, 0xf7, 0xd6),
                _          => DrawColor.FromArgb(0xdc, 0xfc, 0xe7)
            });
        }
        ws1.Cells[ws1.Dimension.Address].AutoFitColumns();

        // ── Sheet 2: Equipment Health ─────────────────────────────────────
        var ws2 = pkg.Workbook.Worksheets.Add("Equipment Health");
        ws2.Cells["A1"].Value = "MTU Engine Fleet — Health Status";
        ws2.Cells["A1:G1"].Merge = true;
        ws2.Cells["A1"].Style.Font.Bold = true;
        ws2.Cells["A1"].Style.Font.Size = 13;
        ws2.Cells["A1"].Style.Fill.PatternType = ExcelFillStyle.Solid;
        ws2.Cells["A1"].Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x06, 0x52, 0x2c));
        ws2.Cells["A1"].Style.Font.Color.SetColor(DrawColor.White);

        var headers2 = new[] { "Engine ID", "Model", "Sector", "Health Score", "Status", "Next Service", "Active Alerts" };
        for (int i = 0; i < headers2.Length; i++)
        {
            var cell = ws2.Cells[3, i + 1];
            cell.Value = headers2[i];
            cell.Style.Font.Bold = true;
            cell.Style.Fill.PatternType = ExcelFillStyle.Solid;
            cell.Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x05, 0x7a, 0x3c));
            cell.Style.Font.Color.SetColor(DrawColor.White);
        }

        for (int r = 0; r < fleet.Units.Count; r++)
        {
            var u = fleet.Units[r];
            ws2.Cells[r + 4, 1].Value = u.EngineId;
            ws2.Cells[r + 4, 2].Value = u.Model;
            ws2.Cells[r + 4, 3].Value = u.Sector;
            ws2.Cells[r + 4, 4].Value = $"{u.HealthScore}%";
            ws2.Cells[r + 4, 5].Value = u.Status;
            ws2.Cells[r + 4, 6].Value = u.NextServiceDue.ToString("yyyy-MM-dd");
            ws2.Cells[r + 4, 7].Value = string.Join("; ", u.ActiveAlerts);

            var statusCell = ws2.Cells[r + 4, 5];
            statusCell.Style.Fill.PatternType = ExcelFillStyle.Solid;
            statusCell.Style.Fill.BackgroundColor.SetColor(u.Status switch
            {
                "Critical" => DrawColor.FromArgb(0xfe, 0xca, 0xca),
                "Warning"  => DrawColor.FromArgb(0xfe, 0xf3, 0xc7),
                _          => DrawColor.FromArgb(0xd1, 0xfa, 0xe5)
            });
        }
        ws2.Cells[ws2.Dimension.Address].AutoFitColumns();

        // ── Sheet 3: MRO Schedule ──────────────────────────────────────────
        var ws3 = pkg.Workbook.Worksheets.Add("MRO Schedule");
        ws3.Cells["A1"].Value = "MTU Engine MRO Schedule";
        ws3.Cells["A1:G1"].Merge = true;
        ws3.Cells["A1"].Style.Font.Bold = true;
        ws3.Cells["A1"].Style.Font.Size = 13;
        ws3.Cells["A1"].Style.Fill.PatternType = ExcelFillStyle.Solid;
        ws3.Cells["A1"].Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x4a, 0x1d, 0x96));
        ws3.Cells["A1"].Style.Font.Color.SetColor(DrawColor.White);

        var headers3 = new[] { "Engine ID", "Model", "Sector", "Interval (h)", "Remaining (h)", "Next Service", "Status" };
        for (int i = 0; i < headers3.Length; i++)
        {
            var cell = ws3.Cells[3, i + 1];
            cell.Value = headers3[i];
            cell.Style.Font.Bold = true;
            cell.Style.Fill.PatternType = ExcelFillStyle.Solid;
            cell.Style.Fill.BackgroundColor.SetColor(DrawColor.FromArgb(0x5b, 0x21, 0xb6));
            cell.Style.Font.Color.SetColor(DrawColor.White);
        }

        for (int r = 0; r < sched.Count; r++)
        {
            var s = sched[r];
            ws3.Cells[r + 4, 1].Value = s.EngineId;
            ws3.Cells[r + 4, 2].Value = s.Model;
            ws3.Cells[r + 4, 3].Value = s.Sector;
            ws3.Cells[r + 4, 4].Value = s.IntervalHours;
            ws3.Cells[r + 4, 5].Value = s.HoursRemaining;
            ws3.Cells[r + 4, 6].Value = s.NextServiceDue.ToString("yyyy-MM-dd");
            ws3.Cells[r + 4, 7].Value = s.Status;
        }
        ws3.Cells[ws3.Dimension.Address].AutoFitColumns();

        return pkg.GetAsByteArray();
    }

    // ── PDF ──────────────────────────────────────────────────────────────────

    private byte[] GeneratePdf(
        ReportRequest req,
        List<AlertDto> alerts,
        FleetHealthSummary fleet,
        IReadOnlyList<MaintenanceSchedule> sched,
        string reportId)
    {
        return Document.Create(doc =>
        {
            doc.Page(page =>
            {
                page.Size(PageSizes.A4.Landscape());
                page.Margin(30);
                page.DefaultTextStyle(t => t.FontFamily("Arial").FontSize(9));

                page.Header().Column(col =>
                {
                    col.Item().Row(row =>
                    {
                        row.RelativeItem().Text(req.Title)
                            .FontSize(16).Bold().FontColor(Colors.White);
                        row.ConstantItem(200).AlignRight().Text(
                            $"Report ID: {reportId}\n{DateTime.UtcNow:yyyy-MM-dd HH:mm} UTC")
                            .FontSize(8).FontColor(Colors.White);
                    });
                    col.Item().PaddingTop(4).Text(
                        $"Fleet: {fleet.TotalUnits} units | Health: {fleet.AverageHealthScore}% avg | " +
                        $"Critical: {fleet.Critical} | Alerts: {alerts.Count}")
                        .FontSize(8).FontColor(Colors.Grey.Lighten3);
                });

                page.Content().PaddingTop(10).Column(col =>
                {
                    // ── Alert table ─────────────────────────────────────
                    if (alerts.Count > 0)
                    {
                        col.Item().Text("Supply Chain Alerts").FontSize(11).Bold()
                            .FontColor(Colors.Blue.Medium);
                        col.Item().PaddingTop(4).Table(tbl =>
                        {
                            tbl.ColumnsDefinition(c =>
                            {
                                c.ConstantColumn(55);  // Ticker
                                c.ConstantColumn(60);  // Severity
                                c.ConstantColumn(60);  // Impact
                                c.RelativeColumn();    // Description
                                c.ConstantColumn(90);  // Timestamp
                            });
                            tbl.Header(h =>
                            {
                                foreach (var hdr in new[] { "TICKER", "SEVERITY", "IMPACT %", "DESCRIPTION", "TIMESTAMP" })
                                    h.Cell().Background(Colors.Blue.Darken3)
                                        .Padding(4).Text(hdr).Bold().FontColor(Colors.White).FontSize(8);
                            });
                            foreach (var a in alerts.Take(20))
                            {
                                tbl.Cell().Padding(3).Text(a.Ticker).FontSize(8);
                                var sevColor = a.Severity.ToUpper() switch
                                {
                                    "HIGH" or "CRITICAL" => Colors.Red.Medium,
                                    "MEDIUM"             => Colors.Orange.Medium,
                                    _                    => Colors.Green.Medium
                                };
                                tbl.Cell().Padding(3).Text(a.Severity.ToUpper())
                                    .Bold().FontColor(sevColor).FontSize(8);
                                tbl.Cell().Padding(3).Text($"{a.ImpactPercent:+0.00;-0.00}%").FontSize(8);
                                tbl.Cell().Padding(3).Text(a.Description[..Math.Min(a.Description.Length, 80)]).FontSize(7);
                                tbl.Cell().Padding(3).Text(a.Timestamp[..Math.Min(a.Timestamp.Length, 19)]).FontSize(7);
                            }
                        });
                        col.Item().PaddingTop(12);
                    }

                    // ── Equipment health table ──────────────────────────
                    col.Item().Text("MTU Fleet Health").FontSize(11).Bold()
                        .FontColor(Colors.Green.Darken2);
                    col.Item().PaddingTop(4).Table(tbl =>
                    {
                        tbl.ColumnsDefinition(c =>
                        {
                            c.RelativeColumn(2);  // Model
                            c.ConstantColumn(65); // Sector
                            c.ConstantColumn(65); // Score
                            c.ConstantColumn(65); // Status
                            c.ConstantColumn(90); // Next service
                        });
                        tbl.Header(h =>
                        {
                            foreach (var hdr in new[] { "MODEL", "SECTOR", "HEALTH", "STATUS", "NEXT SERVICE" })
                                h.Cell().Background(Colors.Green.Darken3)
                                    .Padding(4).Text(hdr).Bold().FontColor(Colors.White).FontSize(8);
                        });
                        foreach (var u in fleet.Units)
                        {
                            tbl.Cell().Padding(3).Text(u.Model).FontSize(8);
                            tbl.Cell().Padding(3).Text(u.Sector).FontSize(8);
                            tbl.Cell().Padding(3).Text($"{u.HealthScore}%").FontSize(8);
                            var sc = u.Status switch
                            {
                                "Critical" => Colors.Red.Medium,
                                "Warning"  => Colors.Orange.Medium,
                                _          => Colors.Green.Medium
                            };
                            tbl.Cell().Padding(3).Text(u.Status).Bold().FontColor(sc).FontSize(8);
                            tbl.Cell().Padding(3).Text(u.NextServiceDue.ToString("yyyy-MM-dd")).FontSize(8);
                        }
                    });
                });

                page.Footer().AlignCenter().Text(t =>
                {
                    t.Span("MarketPulse Enterprise Gateway  ·  Rolls-Royce Power Systems MTU  ·  Page ");
                    t.CurrentPageNumber();
                    t.Span(" of ");
                    t.TotalPages();
                });
            });
        }).GeneratePdf();
    }
}
