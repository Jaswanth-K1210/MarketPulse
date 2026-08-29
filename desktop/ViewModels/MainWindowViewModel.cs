using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarketPulse.Desktop.Services;

namespace MarketPulse.Desktop.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly GatewayService _gateway;

    public DashboardViewModel   Dashboard   { get; }
    public AlertsViewModel      Alerts      { get; }
    public EquipmentViewModel   Equipment   { get; }
    public MaintenanceViewModel Maintenance { get; }
    public ReportsViewModel     Reports     { get; }

    [ObservableProperty] private ViewModelBase _currentPage;
    [ObservableProperty] private string        _currentPageName = "Dashboard";

    public MainWindowViewModel()
    {
        _gateway    = new GatewayService("http://localhost:5000");
        Dashboard   = new DashboardViewModel(_gateway);
        Alerts      = new AlertsViewModel(_gateway);
        Equipment   = new EquipmentViewModel(_gateway);
        Maintenance = new MaintenanceViewModel(_gateway);
        Reports     = new ReportsViewModel(_gateway);
        _currentPage = Dashboard;
    }

    [RelayCommand] public void NavigateDashboard()   => Navigate(Dashboard,   "Dashboard");
    [RelayCommand] public void NavigateAlerts()      => Navigate(Alerts,      "Alerts");
    [RelayCommand] public void NavigateEquipment()   => Navigate(Equipment,   "Equipment");
    [RelayCommand] public void NavigateMaintenance() => Navigate(Maintenance, "Maintenance");
    [RelayCommand] public void NavigateReports()     => Navigate(Reports,     "Reports");

    private void Navigate(ViewModelBase page, string name)
    {
        CurrentPage     = page;
        CurrentPageName = name;
    }
}
