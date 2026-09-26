import type { Metadata } from 'next'
import '@/styles/globals.css'

export const metadata: Metadata = {
    title: 'DocAgent - AI Document Assistant',
    description: 'Intelligent document processing assistant powered by AI',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className="antialiased">{children}</body>
        </html>
    )
}
