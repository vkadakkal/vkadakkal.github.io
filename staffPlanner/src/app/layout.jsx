import './globals.css';

export const metadata = {
  title: 'Staffing Tracker',
  description: 'Track resource allocation and demand',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-text min-h-screen">
        <div className="container mx-auto px-4 py-8">
          {children}
        </div>
      </body>
    </html>
  );
}
