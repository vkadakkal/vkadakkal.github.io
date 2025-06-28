'use client';

import { useState, useEffect } from 'react';
import { useSupabase } from '@/hooks/useSupabase';

export default function OutputTab({ type }) {
  const supabase = useSupabase();
  const [data, setData] = useState([]);

  useEffect(() => {
    if (!supabase) return;

    const fetchData = async () => {
      if (type === 'project') {
        // Calculate: (scaling * demand) - allocation
        const { data: projectData } = await supabase
          .from('projects')
          .select(`
            id,
            name,
            scaling_factor,
            demand:demand(month, fte),
            allocations:allocations(project_id, month, fte)
          `);
        
        const processed = projectData.map(project => {
          const months = {};
          
          // Process demand
          project.demand.forEach(d => {
            months[d.month] = (months[d.month] || 0) + (project.scaling_factor * d.fte);
          });
          
          // Subtract allocations
          project.allocations.forEach(a => {
            months[a.month] = (months[a.month] || 0) - a.fte;
          });
          
          return {
            id: project.id,
            name: project.name,
            months: Object.entries(months).map(([month, value]) => ({
              month,
              value
            }))
          };
        });
        
        setData(processed);
      } else {
        // Calculate: availability - allocation
        const { data: employeeData } = await supabase
          .from('employees')
          .select(`
            id,
            name,
            availability:availability(month, fraction),
            allocations:allocations(month, fte)
          `);
        
        const processed = employeeData.map(employee => {
          const months = {};
          
          // Process availability
          employee.availability.forEach(a => {
            months[a.month] = (months[a.month] || 0) + a.fraction;
          });
          
          // Subtract allocations
          employee.allocations.forEach(a => {
            months[a.month] = (months[a.month] || 0) - a.fte;
          });
          
          return {
            id: employee.id,
            name: employee.name,
            months: Object.entries(months).map(([month, value]) => ({
              month,
              value
            }))
          };
        });
        
        setData(processed);
      }
    };

    fetchData();
  }, [supabase, type]);

  // Get unique months from all data
  const allMonths = [...new Set(data.flatMap(item => item.months.map(m => m.month)))].sort();

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-border">
        <thead>
          <tr>
            <th className="border-b border-border p-3">
              {type === 'project' ? 'Project' : 'Employee'}
            </th>
            {allMonths.map(month => (
              <th key={month} className="border-b border-border p-3">{month}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(item => (
            <tr key={item.id}>
              <td className="border-b border-border p-3">{item.name}</td>
              {allMonths.map(month => {
                const monthData = item.months.find(m => m.month === month);
                const value = monthData ? monthData.value : 0;
                const isNegative = value < 0;
                return (
                  <td 
                    key={`${item.id}-${month}`} 
                    className={`border-b border-border p-3 ${isNegative ? 'text-red-400' : 'text-green-400'}`}
                  >
                    {value.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
