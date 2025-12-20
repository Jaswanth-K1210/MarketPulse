import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const SupplyChainGraphD3 = ({ portfolio, relationships }) => {
  const svgRef = useRef();
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (!portfolio || !relationships) return;

    // Clear previous graph
    d3.select(svgRef.current).selectAll("*").remove();

    // Build graph data
    const nodes = [];
    const links = [];
    const nodeMap = new Map();

    // Add portfolio stocks as nodes
    portfolio.forEach(ticker => {
      const node = {
        id: ticker,
        label: ticker,
        type: 'portfolio',
        value: 100
      };
      nodes.push(node);
      nodeMap.set(ticker, node);
    });

    // Add relationships and related companies
    relationships.forEach(rel => {
      const source = rel.source_ticker || rel.ticker;
      const target = rel.related_company || rel.target_ticker;

      if (!target) return;

      // Add related company as node if not exists
      if (!nodeMap.has(target)) {
        const node = {
          id: target,
          label: target,
          type: rel.type === 'supplier' ? 'supplier' : 'customer',
          value: 60
        };
        nodes.push(node);
        nodeMap.set(target, node);
      }

      // Add link
      links.push({
        source: source,
        target: target,
        type: rel.relationship_type || rel.type,
        criticality: rel.criticality,
        confidence: rel.confidence || 0.8
      });
    });

    // If no relationships, show message
    if (nodes.length === 0) return;

    // D3 Force Simulation
    const width = 800;
    const height = 600;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append('g');

    svg.call(d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      }));

    // Force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    // Draw links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => {
        if (d.criticality === 'CRITICAL' || d.criticality === 'critical') return '#ef4444';
        if (d.criticality === 'HIGH' || d.criticality === 'high') return '#f59e0b';
        return '#6b7280';
      })
      .attr('stroke-width', d => {
        if (d.criticality === 'CRITICAL' || d.criticality === 'critical') return 3;
        if (d.criticality === 'HIGH' || d.criticality === 'high') return 2;
        return 1;
      })
      .attr('stroke-opacity', 0.6);

    // Draw nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => d.type === 'portfolio' ? 25 : 15)
      .attr('fill', d => {
        if (d.type === 'portfolio') return '#8b5cf6';
        if (d.type === 'supplier') return '#06b6d4';
        return '#10b981';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded))
      .on('click', (event, d) => {
        setSelectedNode(d);
      });

    // Add labels
    const label = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text(d => d.label)
      .attr('font-size', 12)
      .attr('font-weight', d => d.type === 'portfolio' ? 'bold' : 'normal')
      .attr('fill', '#fff')
      .attr('text-anchor', 'middle')
      .attr('dy', 4);

    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

    // Drag functions
    function dragStarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragEnded(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

  }, [portfolio, relationships]);

  return (
    <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
          Supply Chain Network
        </h3>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span className="text-slate-400">Portfolio</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-cyan-500"></div>
            <span className="text-slate-400">Suppliers</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
            <span className="text-slate-400">Customers</span>
          </div>
        </div>
      </div>

      <svg ref={svgRef} className="border border-slate-800 rounded-lg bg-slate-950/50 w-full"></svg>

      {selectedNode && (
        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
          <h4 className="text-xs font-bold text-purple-400 mb-2">Selected: {selectedNode.label}</h4>
          <p className="text-xs text-slate-400">Type: {selectedNode.type}</p>
        </div>
      )}
    </div>
  );
};

export default SupplyChainGraphD3;
