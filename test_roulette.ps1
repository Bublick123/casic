# test_roulette.ps1
Write-Host "=== TESTING ROULETTE ===" -ForegroundColor Green

# Базовый URL
$BASE_URL = "http://localhost"

# 1. Регистрация
Write-Host "1. Registering user..." -ForegroundColor Yellow
$registerBody = @{
    login = "powershell_test"
    email = "powershell@test.com"
    password = "Test123!"
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    Write-Host "Register success: $($registerResponse | ConvertTo-Json)" -ForegroundColor Green
}
catch {
    Write-Host "Register error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host "Testing game-service directly..." -ForegroundColor Yellow
try {
    $directHealth = Invoke-RestMethod -Uri "http://localhost:8003/health"
    Write-Host "Game service direct health: $($directHealth | ConvertTo-Json)" -ForegroundColor Green
}
catch {
    Write-Host "Game service direct error: $($_.Exception.Message)" -ForegroundColor Red
}

# Проверим roulette test напрямую
try {
    $directTest = Invoke-RestMethod -Uri "http://localhost:8003/roulette/test" -Headers @{Authorization = "Bearer $TOKEN"}
    Write-Host "Roulette test direct: $($directTest | ConvertTo-Json)" -ForegroundColor Green
}
catch {
    Write-Host "Roulette test direct error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Логин
Write-Host "2. Logging in..." -ForegroundColor Yellow
$loginBody = @{
    login = "powershell_test"
    password = "Test123!"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $TOKEN = $loginResponse.access_token
    Write-Host "Login success! Token: $($TOKEN.Substring(0, 20))..." -ForegroundColor Green
}
catch {
    Write-Host "Login error: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 3. Депозит
Write-Host "3. Making deposit..." -ForegroundColor Yellow
$depositQuery = @{
    query = 'mutation { createTransaction(type: "deposit", amount: 500.0) { ... on TransactionSuccess { transaction { id amount } } } }'
} | ConvertTo-Json

try {
    $depositResponse = Invoke-RestMethod -Uri "$BASE_URL/graphql" -Method Post -Body $depositQuery -ContentType "application/json" -Headers @{Authorization = "Bearer $TOKEN"}
    Write-Host "Deposit success: $($depositResponse | ConvertTo-Json -Depth 3)" -ForegroundColor Green
}
catch {
    Write-Host "Deposit error: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Создание игры
Write-Host "4. Creating roulette game..." -ForegroundColor Yellow
try {
    $gameResponse = Invoke-RestMethod -Uri "$BASE_URL/games/roulette/games" -Method Post -Headers @{Authorization = "Bearer $TOKEN"} -ContentType "application/json"
    $GAME_ID = $gameResponse.id
    Write-Host "Game created! ID: $GAME_ID" -ForegroundColor Green
    Write-Host "Game details: $($gameResponse | ConvertTo-Json)" -ForegroundColor Cyan
}
catch {
    Write-Host "Game creation error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
    exit
}

# 5. Ставка (ИСПРАВЛЕННЫЙ URL)
Write-Host "5. Placing bet..." -ForegroundColor Yellow
$betBody = @{
    bet_type = "red"
    numbers = @()
    amount = 50.0
} | ConvertTo-Json

try {
    # ИСПРАВЛЕННЫЙ URL - добавил / перед bet
    $betResponse = Invoke-RestMethod -Uri "$BASE_URL/games/roulette/games/$GAME_ID/bet" -Method Post -Body $betBody -ContentType "application/json" -Headers @{Authorization = "Bearer $TOKEN"}
    Write-Host "Bet placed: $($betResponse | ConvertTo-Json)" -ForegroundColor Green
}
catch {
    Write-Host "Bet error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Full error: $($_.Exception)" -ForegroundColor Red
}
# 6. Проверка игр
Write-Host "6. Checking games..." -ForegroundColor Yellow
try {
    $gamesResponse = Invoke-RestMethod -Uri "$BASE_URL/games/roulette/games" -Headers @{Authorization = "Bearer $TOKEN"}
    Write-Host "Games list: $($gamesResponse | ConvertTo-Json -Depth 3)" -ForegroundColor Cyan
}
catch {
    Write-Host "Games list error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "=== TEST COMPLETE ===" -ForegroundColor Green