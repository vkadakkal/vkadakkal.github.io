import { useState } from 'react';

export const Tabs = ({ children }) => {
  const [activeTab, setActiveTab] = useState(0);
  return (
    <div>
      <div className="flex border-b border-border mb-4">
        {children.map((child, index) => (
          <button
            key={index}
            className={`py-2 px-4 font-medium text-sm ${
              activeTab === index
                ? 'border-b-2 border-primary text-primary'
                : 'text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => setActiveTab(index)}
          >
            {child.props.label}
          </button>
        ))}
      </div>
      <div>
        {children[activeTab]}
      </div>
    </div>
  );
};

export const Tab = ({ children }) => {
  return <div className="mt-4">{children}</div>;
};
