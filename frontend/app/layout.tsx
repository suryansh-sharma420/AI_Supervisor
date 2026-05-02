import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'
import { ToastProvider } from '@/components/ui/Toast'

export const metadata: Metadata = {
  title: 'Order Supervisor',
  description: 'Mission Control',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <ToastProvider>
          <Sidebar />
          <main className="ml-[220px] min-h-screen">
            {children}
          </main>
        </ToastProvider>
      </body>
    </html>
  )
}
