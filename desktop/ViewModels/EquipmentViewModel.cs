using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Models;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class EquipmentViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    [ObservableProperty] private ObservableCollection<EquipmentHealth> _units = new();
    [ObservableProperty] private bool   _isLoading;
    [ObservableProperty] private string _statusMessage = "Click Refresh to load fleet health";
    [ObservableProperty] private int    _healthy;
    [ObservableProperty] private int    _warning;
    [ObservableProperty] private int    _critical;
    [ObservableProperty] private int    _averageScore;

    public EquipmentViewModel(GatewayService gateway)
    {
        _gateway = gateway;
    }

    [RelayCommand]
    public async Task RefreshAsync()
    {
        IsLoading = true;
        StatusMessage = "Loading fleet health…";
        try
        {
            var fleet = await _gateway.GetFleetHealthAsync();
            Units.Clear();
            if (fleet?.Units != null)
            {
                foreach (var u in fleet.Units) Units.Add(u);
                Healthy      = fleet.Healthy;
                Warning      = fleet.Warning;
                Critical     = fleet.Critical;
                AverageScore = fleet.AverageHealthScore;
            }
            StatusMessage = $"{Units.Count} unit(s) loaded — {DateTime.Now:HH:mm:ss}";
        }
        catch (Exception ex)
        {
            StatusMessage = $"Error: {ex.Message}";
        }
        finally { IsLoading = false; }
    }
}
