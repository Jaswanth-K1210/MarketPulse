using Microsoft.AspNetCore.Mvc;
using MarketPulse.Gateway.Services;

namespace MarketPulse.Gateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class EquipmentController : ControllerBase
{
    private readonly EquipmentHealthService _health;

    public EquipmentController(EquipmentHealthService health) => _health = health;

    /// <summary>Fleet-wide health summary — KPIs and per-unit table.</summary>
    [HttpGet("health")]
    public IActionResult GetFleetHealth()
        => Ok(_health.GetFleetSummary());

    /// <summary>Health detail for a single engine unit.</summary>
    [HttpGet("{engineId}/health")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult GetUnitHealth(string engineId)
    {
        var unit = _health.GetById(engineId);
        if (unit is null)
            return NotFound(new { error = $"Engine {engineId} not found." });
        return Ok(unit);
    }

    /// <summary>Active alert list across the entire fleet (aggregated).</summary>
    [HttpGet("alerts")]
    public IActionResult GetFleetAlerts()
    {
        var units = _health.GetFleetSummary().Units;
        var alerts = units
            .SelectMany(u => u.ActiveAlerts.Select(msg => new
            {
                engineId = u.EngineId,
                model    = u.Model,
                sector   = u.Sector,
                status   = u.Status,
                message  = msg
            }))
            .ToList();

        return Ok(new { count = alerts.Count, alerts });
    }

    /// <summary>All units in a specific status (Healthy, Warning, Critical).</summary>
    [HttpGet("status/{status}")]
    public IActionResult GetByStatus(string status)
    {
        var units = _health.GetByStatus(status);
        return Ok(new { count = units.Count, units });
    }

    /// <summary>Sensor readings for a single engine.</summary>
    [HttpGet("{engineId}/sensors")]
    [ProducesResponseType(200)]
    [ProducesResponseType(404)]
    public IActionResult GetSensors(string engineId)
    {
        var unit = _health.GetById(engineId);
        if (unit is null)
            return NotFound(new { error = $"Engine {engineId} not found." });

        return Ok(new
        {
            engineId       = unit.EngineId,
            model          = unit.Model,
            healthScore    = unit.HealthScore,
            sensors        = unit.SensorReadings,
            operatingHours = unit.OperatingHours,
            sampledAt      = DateTime.UtcNow
        });
    }
}
