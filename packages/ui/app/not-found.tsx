export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-4">
      <div className="text-center space-y-4">
        <h2 className="text-2xl font-bold">404 - Not Found</h2>
        <p className="text-muted-foreground">
          The page you are looking for does not exist.
        </p>
        <a href="/" className="text-primary hover:underline">
          Go back home
        </a>
      </div>
    </div>
  );
}
