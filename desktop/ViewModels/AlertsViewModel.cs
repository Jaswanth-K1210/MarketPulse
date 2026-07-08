using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Models;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class AlertsViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    [ObservableProperty] private ObservableCollection<AlertDto> _alerts = new();
    [ObservableProperty] private bool   _isLoading;
    [ObservableProperty] private string _statusMessage = "Click Refresh to load alerts";
    [ObservableProperty] private string _severityFilter = "all";
    [ObservableProperty] private int    _limitFilter    = 20;

    public List<string> SeverityOptions { get; } = new() { "all", "low", "medium", "high", "critical" };
    public List<int>    LimitOptions    { get; } = new() { 10, 20, 50, 100 };

    public AlertsViewModel(GatewayService gateway)
    {
        _gateway = gateway;
    }

    [RelayCommand]
    public async Task RefreshAsync()
    {
        IsLoading = true;
        StatusMessage = "Loading alerts…";
        try
        {
            var sev  = SeverityFilter == "all" ? null : SeverityFilter;
            var resp = await _gateway.GetAlertsAsync(sev, LimitFilter);
            Alerts.Clear();
            if (resp?.Alerts != null)
                foreach (var a in resp.Alerts)
                    Alerts.Add(a);
            StatusMessage = $"{Alerts.Count} alert(s) loaded — {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error: {ex.Message}";
        }
        finally { IsLoading = false; }
    }
}
