using System;
using System.Diagnostics.CodeAnalysis;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using MarketPulse.Desktop.ViewModels;

namespace MarketPulse.Desktop;

/// <summary>
/// Given a view model, returns the corresponding view if possible.
/// </summary>
[RequiresUnreferencedCode(
    "Default implementation of ViewLocator involves reflection which may be trimmed away.",
    Url = "https://docs.avaloniaui.net/docs/concepts/view-locator")]
public class ViewLocator : IDataTemplate
{
    public Control? Build(object? param)
    {
        if (param is null)
            return null;

        // e.g. MarketPulse.Desktop.ViewModels.DashboardViewModel
        //   →  MarketPulse.Desktop.Views.DashboardView
        var vmName   = param.GetType().FullName!;
        var viewName = vmName
            .Replace(".ViewModels.", ".Views.", StringComparison.Ordinal)
            .Replace("ViewModel", "View", StringComparison.Ordinal);

        var type = Type.GetType(viewName);
        if (type != null)
            return (Control)Activator.CreateInstance(type)!;

        return new TextBlock { Text = "View not found: " + viewName };
    }

    public bool Match(object? data)
    {
        return data is ViewModelBase;
    }
}
