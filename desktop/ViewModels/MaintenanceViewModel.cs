using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Models;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class MaintenanceViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    [ObservableProperty] private ObservableCollection<MaintenanceSchedule> _schedules = new();
    [ObservableProperty] private bool   _isLoading;
    [ObservableProperty] private string _statusMessage    = "Click Refresh to load MRO schedule";
    [ObservableProperty] private string _triggerResult    = string.Empty;
    [ObservableProperty] private MaintenanceSchedule? _selectedSchedule;

    public MaintenanceViewModel(GatewayService gateway)
    {
        _gateway = gateway;
    }

    [RelayCommand]
    public async Task RefreshAsync()
    {
        IsLoading = true;
        StatusMessage = "Loading MRO schedule…";
        try
        {
            var list = await _gateway.GetMaintenanceScheduleAsync();
            Schedules.Clear();
            if (list != null) foreach (var s in list) Schedules.Add(s);
            StatusMessage = $"{Schedules.Count} engine(s) loaded — {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error: {ex.Message}";
        }
        finally { IsLoading = false; }
    }

    [RelayCommand]
    public async Task TriggerMaintenanceAsync()
    {
        if (SelectedSchedule is null) return;
        IsLoading = true;
        TriggerResult = "Creating work order…";
        var (ok, msg) = await _gateway.TriggerMaintenanceAsync(SelectedSchedule.EngineId);
        TriggerResult = ok ? $"✓ Work order created for {SelectedSchedule.EngineId}" : $"✗ {msg}";
        IsLoading = false;
        await RefreshAsync();
    }
}
