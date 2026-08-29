using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Models;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class DashboardViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    [ObservableProperty] private int    _totalUnits;
    [ObservableProperty] private int    _healthyUnits;
    [ObservableProperty] private int    _warningUnits;
    [ObservableProperty] private int    _criticalUnits;
    [ObservableProperty] private int    _averageHealth;
    [ObservableProperty] private string _overallStatus    = "Unknown";
    [ObservableProperty] private int    _alertCount;
    [ObservableProperty] private int    _overdueCount;
    [ObservableProperty] private bool   _isLoading;
    [ObservableProperty] private bool   _isConnected;
    [ObservableProperty] private string _connectionText   = "Disconnected";
    [ObservableProperty] private string _statusMessage    = "Click Refresh to load data";
    [ObservableProperty] private string _gatewayUrl       = "http://localhost:5000";

    public DashboardViewModel(GatewayService gateway)
    {
        _gateway = gateway;
    }

    [RelayCommand]
    public async Task RefreshAsync()
    {
        IsLoading   = true;
        StatusMessage = "Connecting to gateway…";

        IsConnected = await _gateway.CheckHealthAsync();
        if (!IsConnected)
        {
            StatusMessage = $"⚠ Gateway unreachable at {_gateway.BaseUrl} — start the .NET gateway first.";
            IsLoading = false;
            return;
        }

        try
        {
            var fleetTask  = _gateway.GetFleetHealthAsync();
            var alertTask  = _gateway.GetAlertsAsync(limit: 50);
            var maintTask  = _gateway.GetMaintenanceScheduleAsync();

            await Task.WhenAll(fleetTask, alertTask, maintTask);

            var fleet = await fleetTask;
            if (fleet != null)
            {
                TotalUnits     = fleet.TotalUnits;
                HealthyUnits   = fleet.Healthy;
                WarningUnits   = fleet.Warning;
                CriticalUnits  = fleet.Critical;
                AverageHealth  = fleet.AverageHealthScore;
                OverallStatus  = fleet.OverallStatus;
            }

            var alerts = await alertTask;
            AlertCount = alerts?.Count ?? 0;

            var maint = await maintTask;
            OverdueCount = maint?.Count(m => m.Status == "Overdue") ?? 0;

            StatusMessage = $"Last updated: {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error: {ex.Message}";
        }
        finally
        {
            IsLoading = false;
        }
    }
}
