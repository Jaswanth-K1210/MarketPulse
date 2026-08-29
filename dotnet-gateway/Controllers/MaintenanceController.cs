using Microsoft.AspNetCore.Mvc;
using MarketPulse.Gateway.Services;

namespace MarketPulse.Gateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class MaintenanceController : ControllerBase
{
    private readonly MaintenanceService _maint;
    private readonly ILogger<MaintenanceController> _log;

    public MaintenanceController(MaintenanceService maint, ILogger<MaintenanceController> log)
    {
        _maint = maint;
        _log   = log;
    }

    /// <summary>Full MRO schedule for all MTU engines.</summary>
    [HttpGet("schedule")]
    public IActionResult GetSchedule()
        => Ok(_maint.GetAll());

    /// <summary>Engines whose service interval is overdue.</summary>
    [HttpGet("overdue")]
    public IActionResult GetOverdue()
    {
        var overdue = _maint.GetOverdue();
        return Ok(new
        {
            count   = overdue.Count,
            engines = overdue
        });
    }

    /// <summary>Engines in Warning or Overdue state.</summary>
    [HttpGet("warnings")]
    public IActionResult GetWarnings()
    {
        var warnings = _maint.GetWarning();
        return Ok(new
        {
            count   = warnings.Count,
            engines = warnings
        });
    }

    /// <summary>Maintenance schedule for a single engine.</summary>
    [HttpGet("{engineId}")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult GetById(string engineId)
    {
        var sched = _maint.GetById(engineId);
        if (sched is null)
            return NotFound(new { error = $"Engine {engineId} not found." });
        return Ok(sched);
    }

    /// <summary>Create a maintenance work order for an engine.</summary>
    [HttpPost("trigger/{engineId}")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult TriggerMaintenance(string engineId)
    {
        var result = _maint.TriggerMaintenance(engineId);
        if (!result.Success)
            return NotFound(new { error = result.Message });

        _log.LogInformation("Work order {WorkOrder} created for {EngineId}", result.WorkOrder, engineId);
        return Ok(result);
    }
}
