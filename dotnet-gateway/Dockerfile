FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY MarketPulse.Gateway.csproj .
RUN dotnet restore

COPY . .
RUN dotnet publish -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:5000
ENV ASPNETCORE_ENVIRONMENT=Production

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:5000/health || exit 1

EXPOSE 5000
ENTRYPOINT ["dotnet", "MarketPulse.Gateway.dll"]
