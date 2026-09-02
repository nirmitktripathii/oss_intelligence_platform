import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/theme/theme-provider';
import { ToastProvider } from '@/components/ui/toast';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import { PlatformJsonLd } from '@/components/seo/json-ld';
import { DEFAULT_METADATA } from '@/lib/seo-config';
import { SpeedInsights } from '@vercel/speed-insights/next';
import { Analytics } from '@vercel/analytics/react';

export const metadata: Metadata = DEFAULT_METADATA;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-skin="tokyo" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        {/* Restore the persisted skin before first paint to avoid a flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var s=localStorage.getItem('gitscout-skin');var allowed=['tokyo','phosphor','amber','brutalist','rosepine'];if(s&&allowed.indexOf(s)!==-1){document.documentElement.setAttribute('data-skin',s);}}catch(e){}})();`,
          }}
        />
        {/* Skin typefaces — IBM Plex, JetBrains Mono, VT323, Archivo, Fraunces */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=VT323&display=swap"
        />
        <PlatformJsonLd />
      </head>
      <body className="min-h-screen bg-background text-foreground flex flex-col selection:bg-primary selection:text-primary-foreground">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <ToastProvider>
            <Header />
            <main className="flex-1 w-full">{children}</main>
            <Footer />
          </ToastProvider>
        </ThemeProvider>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
}
