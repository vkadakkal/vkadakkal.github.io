'use client';

import { Tabs, Tab } from '@/components/Tabs';
import EmployeeTab from '@/components/EmployeeTab';
import DemandTab from '@/components/DemandTab';
import AllocationTab from '@/components/AllocationTab';
import OutputTab from '@/components/OutputTab';

export default function StaffingTracker() {
  return (
    <div className="card">
      <h1 className="text-2xl font-bold mb-6 text-primary">Staffing Tracker</h1>
      <Tabs>
        <Tab label="Employees">
          <EmployeeTab />
        </Tab>
        <Tab label="Demand">
          <DemandTab />
        </Tab>
        <Tab label="Allocation">
          <AllocationTab />
        </Tab>
        <Tab label="Project Output">
          <OutputTab type="project" />
        </Tab>
        <Tab label="Resource Loading">
          <OutputTab type="resource" />
        </Tab>
      </Tabs>
    </div>
  );
}
