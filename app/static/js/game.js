/**
 * QS PRO - Core Logic & Cyber-Runner Game
 */

window.triggerGame = function() {
    window.dispatchEvent(new CustomEvent('open-arcade'));
    setTimeout(() => {
        const canvas = document.getElementById('gameCanvas');
        if (canvas) {
            initGame();
        } else {
            console.error("[ СИСТЕМА ] Холст игры не загрузился.");
        }
    }, 150);
};

document.body.addEventListener('htmx:responseError', (event) => {
    if (event.detail.xhr.status === 500) {
        window.triggerGame();
    }
});

let gameLoop; 

function initGame() {
    const canvas = document.getElementById('gameCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let isGameOver = false;
    let score = 0;
    let frame = 0;
    let nextSpawnFrame = 60; // Первое препятствие появится через 1 секунду
    
    const playerSize = 25;
    const groundY = canvas.height - 60; 
    let playerY = groundY - playerSize;
    let velocityY = 0;
    const gravity = 0.6;
    const jumpPower = -11.5; // Чуть усилили прыжок для высоких скоростей
    
    let obstacles = [];

    if (gameLoop) cancelAnimationFrame(gameLoop);

    function step() {
        if (isGameOver) return;

        // 1. Физика
        velocityY += gravity;
        playerY += velocityY;
        
        if (playerY >= groundY - playerSize) {
            playerY = groundY - playerSize;
            velocityY = 0;
        }

        // 2. Умный спавн (Прогрессивная сложность)
        if (frame >= nextSpawnFrame) {
            let obsHeight = 25 + Math.random() * 45; // Высота от 25 до 70
            obstacles.push({ x: canvas.width, y: groundY - obsHeight, width: 20, height: obsHeight });
            
            // Математика сложности:
            // Базовая пауза начинается со 130 кадров (очень легко) и падает до 45 (очень сложно)
            let baseDelay = Math.max(45, 130 - Math.floor(score / 15));
            // Случайный разброс (от 0 до 40 кадров), чтобы ломать ритм
            let randomVariation = Math.floor(Math.random() * 40); 
            
            nextSpawnFrame = frame + baseDelay + randomVariation;
        }

        // 3. Ускорение игры
        // Начинаем со скорости 3.5 (медленно), максимум - 10.5 (хардкор)
        let gameSpeed = Math.min(10.5, 3.5 + (score / 400));
        
        obstacles.forEach(obs => obs.x -= gameSpeed);
        if (obstacles.length > 0 && obstacles[0].x < -50) obstacles.shift();

        // 4. Отрисовка фона и Земли
        ctx.fillStyle = '#070a13'; 
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.beginPath();
        ctx.moveTo(0, groundY);
        ctx.lineTo(canvas.width, groundY);
        ctx.strokeStyle = '#00f2fe';
        ctx.lineWidth = 2;
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#00f2fe';
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Счёт и Текущая Скорость
        ctx.fillStyle = '#39ff14';
        ctx.font = 'bold 18px monospace';
        ctx.fillText(`СКОРОСТЬ: ${gameSpeed.toFixed(1)}  СЧЕТ: ${score}`, 20, 35);

        // 5. Отрисовка Препятствий и Столкновения
        ctx.fillStyle = '#39ff14'; 
        ctx.shadowBlur = 15;
        ctx.shadowColor = '#39ff14';
        obstacles.forEach(obs => {
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            
            if (50 < obs.x + obs.width && 50 + playerSize > obs.x && playerY + playerSize > obs.y) {
                isGameOver = true;
                ctx.fillStyle = '#ef4444'; 
                ctx.shadowColor = '#ef4444';
                ctx.font = 'black 24px monospace';
                ctx.textAlign = "center";
                ctx.fillText('СИСТЕМА ВЗЛОМАНА', canvas.width / 2, canvas.height / 2 - 20);
                
                ctx.fillStyle = '#6b7280'; 
                ctx.shadowBlur = 0;
                ctx.font = '14px monospace';
                ctx.fillText('Нажми ПРОБЕЛ для рестарта', canvas.width / 2, canvas.height / 2 + 20);
                ctx.textAlign = "left"; 
            }
        });
        ctx.shadowBlur = 0;

        // 6. Отрисовка Игрока
        ctx.fillStyle = '#00f2fe'; 
        ctx.shadowBlur = 20;
        ctx.shadowColor = '#00f2fe';
        ctx.fillRect(50, playerY, playerSize, playerSize);
        ctx.shadowBlur = 0;

        score++;
        frame++;
        
        if (!isGameOver) {
            gameLoop = requestAnimationFrame(step);
        }
    }

    function resetGame() {
        playerY = groundY - playerSize;
        velocityY = 0;
        obstacles = [];
        frame = 0;
        score = 0;
        nextSpawnFrame = 60; // Сброс таймера спавна
        isGameOver = false;
        step(); 
    }

    const jump = (e) => {
        if (e.type === 'keydown' && e.code !== 'Space') return;
        
        if (isGameOver) {
            resetGame();
            if (e.cancelable) e.preventDefault();
            return;
        }

        if (playerY >= groundY - playerSize) {
            velocityY = jumpPower;
        }
        if (e.cancelable) e.preventDefault();
    };

    window.removeEventListener('keydown', jump);
    canvas.removeEventListener('mousedown', jump);
    canvas.removeEventListener('touchstart', jump);

    window.addEventListener('keydown', jump);
    canvas.addEventListener('mousedown', jump);
    canvas.addEventListener('touchstart', jump, {passive: false});

    step();
}

window.resetSnippetForm = function(event) {
    if (event.detail.successful) {
        event.detail.elt.reset();
    }
};