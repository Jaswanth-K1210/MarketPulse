using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class ReportsViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    [ObservableProperty] private string _selectedType  = "excel";
    [ObservableProperty] private bool   _isGenerating;
    [ObservableProperty] private string _resultMessage = string.Empty;
    [ObservableProperty] private string _downloadUrl   = string.Empty;

    public List<string> ReportTypes { get; } = new() { "excel", "pdf" };

    public ReportsViewModel(GatewayService gateway)
    {
        _gateway = gateway;
    }

    [RelayCommand]
    public async Task GenerateAsync()
    {
        IsGenerating  = true;
        ResultMessage = $"Generating {SelectedType.ToUpper()} report…";
        DownloadUrl   = string.Empty;

        var (ok, url, err) = await _gateway.GenerateReportAsync(SelectedType);
        if (ok)
        {
            DownloadUrl   = url ?? string.Empty;
            ResultMessage = $"✓ Report ready — {SelectedType.ToUpper()}";
        }
        else
        {
            ResultMessage = $"✗ Generation failed: {err}";
        }
        IsGenerating = false;
    }

    [RelayCommand]
    public void OpenReport()
    {
        if (string.IsNullOrWhiteSpace(DownloadUrl)) return;
        try { System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(DownloadUrl) { UseShellExecute = true }); }
        catch { ResultMessage = "Could not open file. Copy the URL manually."; }
    }
}
