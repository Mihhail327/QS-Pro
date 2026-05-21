/**
 * QS PRO - Core Logic & Easter Egg Game
 */

// 1. Регистрация Service Worker для PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('SW registered'))
            .catch(err => console.log('SW error', err));
    });
}

// 2. Глобальный обработчик ошибок HTMX
document.body.addEventListener('htmx:responseError', (event) => {
    // Если сервер вернул 500 ошибку
    if (event.detail.xhr.status === 500) {
        // Достукиваемся до данных Alpine.js
        const alpineRoot = document.querySelector('[x-data]');
        if (alpineRoot && alpineRoot.__x) {
            alpineRoot.__x.$data.hasError = true;
            // Запускаем игру, когда Alpine покажет холст
            setTimeout(initGame, 100);
        }
    }
});

// 3. Логика игры "Крипто-Прыжок"
function initGame() {
    const canvas = document.getElementById('gameCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Настройки
    let birdY = 200;
    let birdV = 0;
    let pipes = [];
    let frame = 0;
    let isGameOver = false;

    function step() {
        if (isGameOver) return;

        // Физика
        birdV += 0.25; // Гравитация
        birdY += birdV;

        // Генерация препятствий
        if (frame % 90 === 0) {
            pipes.push({
                x: canvas.width,
                y: Math.random() * (canvas.height - 150) + 50,
                width: 40,
                height: 400
            });
        }

        // Движение препятствий
        pipes.forEach(p => p.x -= 2.5);
        
        // Очистка ушедших за экран
        if (pipes.length > 0 && pipes[0].x < -50) pipes.shift();

        // Отрисовка фона
        ctx.fillStyle = '#111827'; // Tailwind gray-900
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Отрисовка препятствий
        ctx.fillStyle = '#1f2937'; // Tailwind gray-800
        pipes.forEach(p => {
            ctx.fillRect(p.x, p.y, p.width, p.height);
            // Проверка столкновений
            if (50 + 20 > p.x && 50 < p.x + p.width && birdY + 20 > p.y) {
                resetGame();
            }
        });

        // Отрисовка игрока (Квадрат-сниппет)
        ctx.fillStyle = '#3b82f6'; // Tailwind blue-500
        ctx.shadowBlur = 15;
        ctx.shadowColor = '#3b82f6';
        ctx.fillRect(50, birdY, 20, 20);
        ctx.shadowBlur = 0; // Сброс тени для остального

        // Проверка падения
        if (birdY > canvas.height || birdY < -50) {
            resetGame();
        }

        frame++;
        requestAnimationFrame(step);
    }

    function resetGame() {
        birdY = 200;
        birdV = 0;
        pipes = [];
        frame = 0;
    }

    // Управление
    const jump = (e) => {
        if (e.type === 'keydown' && e.code !== 'Space') return;
        birdV = -5;
        if (e.cancelable) e.preventDefault();
    };

    window.addEventListener('keydown', jump);
    canvas.addEventListener('mousedown', jump);
    canvas.addEventListener('touchstart', jump, {passive: false});

    // Поехали!
    step();
}

/**
 * Хелпер для очистки формы после HTMX запроса
 * Вызывается через @htmx:after-request в HTML
 */
window.resetSnippetForm = function(event) {
    if (event.detail.successful) {
        event.detail.elt.reset();
    }
};