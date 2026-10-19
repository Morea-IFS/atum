const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const eventId = document.body.dataset.eventId;
let socket;

function connect() {
    socket = new WebSocket(protocol + window.location.host + "/ws/scoreboard/" + eventId + "/");
    socket.addEventListener('open', () => console.log('WebSocket aberto'));
    socket.onmessage = handleMessage;
    socket.onclose = (e) => {
        console.error('WebSocket fechado com código: ' + e.code);
        if (futsalCycleInterval) clearInterval(futsalCycleInterval);
        setTimeout(connect, 3000);
    };
}

const timer = document.getElementById('timer');

// Variáveis globais para controle do ciclo
let futsalCycleInterval;
let currentFutsalTeam = 'a'; // 'a' para casa, 'b' para visitante
let futsalPlayersA = [];
let futsalPlayersB = [];

connect();

function handleMessage(e) {
    const data = JSON.parse(e.data);

    console.log("Mensagem recebida:", data);

    switch (data.type) {
        case "match":
            console.log("match");
            const match = data.data;

            const sexo_match = document.getElementById('sexo');
            const sport_match = document.getElementById('sport');
            if(match.match_sexo === "Nenhum" && match.match_sport === "Nenhum"){
                const timer = document.getElementById('timer');
                if (timer) timer.textContent = "00:00";
            }
            const namescore = document.getElementById('name-scoreboard');

            const sets_a_match = document.getElementById('sets-a');
            const sets_b_match = document.getElementById('sets-b');
            const ball_sport = document.getElementById('ball-sport');

            const team_name_a_match = document.getElementById('team-name-a');
            const team_photo_a_match = document.getElementById('team-photo-a');
            const card_a_match = document.getElementById('card-a');
            const lack_a_match = document.getElementById('lack-a');
            const aces_a_match = document.getElementById('aces-a');
            const point_a_match = document.getElementById('point-a');
            const photoA_match = document.getElementById('team-photo-a');
            
            const team_name_b_match = document.getElementById('team-name-b');
            const team_photo_b_match = document.getElementById('team-photo-b');
            const card_b_match = document.getElementById('card-b');
            const lack_b_match = document.getElementById('lack-b');
            const aces_b_match = document.getElementById('aces-b');
            const point_b_match = document.getElementById('point-b');
            const photoB_match = document.getElementById('team-photo-b');

            if (team_name_a_match) team_name_a_match.textContent = match.team_name_a;
            if (team_photo_a_match) team_photo_a_match.textContent = match.team_photo_a;
            if (card_a_match) card_a_match.textContent = match.card_a;
            if (lack_a_match) lack_a_match.textContent = match.lack_a;
            if (point_a_match) point_a_match.textContent = match.point_a;
            if (photoA_match) photoA_match.src = match.photoA;

            if (team_name_b_match) team_name_b_match.textContent = match.team_name_b;
            if (team_photo_b_match) team_photo_b_match.textContent = match.team_photo_b;
            if (card_b_match) card_b_match.textContent = match.card_b;
            if (lack_b_match) lack_b_match.textContent = match.lack_b;
            if (point_b_match) point_b_match.textContent = match.point_b;
            if (photoB_match) photoB_match.src = match.photoB;

            applyTeamColors(match.colorA, match.colorB);
        
            if(match.aces_a && match.aces_b){
                if (aces_a_match) aces_a_match.textContent = match.aces_a;
                if (aces_b_match) aces_b_match.textContent = match.aces_b;
            }

            const aces = document.querySelectorAll(".aces");
            const sets = document.querySelectorAll(".sets");
            const timer = document.querySelectorAll(".timer");

            sets.forEach((i) => {
                i.style.display = 'none';
            });
            timer.forEach((j) => {
                j.style.display = 'flex';
            });

            if(match.match_sport === "Voleibol" || match.match_sport === "Voleibol sentado"){
                aces.forEach((t) => {
                    t.style.display = 'flex';
                });
                sets.forEach((i) => {
                    i.style.display = 'flex';
                });
                timer.forEach((j) => {
                    j.style.display = 'none';
                });
                if (sets_a_match) sets_a_match.textContent = match.sets_a;
                if (sets_b_match) sets_b_match.textContent = match.sets_b;

                console.log("Vôlei");
                if (namescore) namescore.textContent = "Sets";
                if(ball_sport) ball_sport.src = '/static/images/ball-of-volley.png';

            }else{
                console.log("Outro esporte");
                aces.forEach((t) => {
                    t.style.display = 'none';
                });
                sets.forEach((i) => {
                    i.style.display = 'none';
                });
                timer.forEach((j) => {
                    j.style.display = 'flex';
                });
                if (sets_a_match) sets_a_match.textContent = "0";
                if (sets_b_match) sets_b_match.textContent = "0";
                if (namescore) namescore.textContent = "Placar";
                if(ball_sport) ball_sport.src = '/static/images/ball-of-futsal.png';
            }
            if(match.match_sport === "Handebol"){
                if(ball_sport) ball_sport.src = '/static/images/ball-of-handball.png';
            }

            const scorematch = document.querySelectorAll('.score-ban');
            const cvolleyball = document.getElementById('container-volleyball')
            const cfutsal = document.getElementById('container-futsal')
            const moments = document.getElementById('moments')
            const end = document.getElementById('end')
            
            if(match.detailed == "Escalação" && match.match_sport === "Voleibol"){
                scorematch.forEach((k) => {
                    k.style.display = 'none';
                });
                if(cvolleyball) cvolleyball.style.display = "flex";
                if(cfutsal) cfutsal.style.display = "none";
                if(moments) moments.style.display = "none";
                if(end) end.style.display = "none";
                
                // Preencher escalação do vôlei
                preencherEscalacaoVolei(match.lineup.players_a, match.lineup.players_b);

            }else if(match.detailed == "Em instantes"){
                scorematch.forEach((k) => {
                    k.style.display = 'none';
                });
                if(cvolleyball) cvolleyball.style.display = "none";
                if(cfutsal) cfutsal.style.display = "none";
                if(moments) moments.style.display = "flex";
                if(end) end.style.display = "none";

                const team_name_a_mat = document.getElementById('moments-team-name-a');
                const team_photo_a_mat = document.getElementById('moments-team-photo-a');
                const team_name_b_mat = document.getElementById('moments-team-name-b');
                const team_photo_b_mat = document.getElementById('moments-team-photo-b');
                if (team_name_a_mat) team_name_a_mat.textContent = match.team_name_a;
                if (team_photo_a_mat) team_photo_a_mat.src = match.photoA;
                if (team_name_b_mat) team_name_b_mat.textContent = match.team_name_b;
                if (team_photo_b_mat) team_photo_b_mat.src = match.photoB;
                
                // Preencher escalação do vôlei
                preencherEscalacaoVolei(match.players_a, match.players_b);

            }else if(match.detailed == "Penaltis" && match.match_sport !== "Voleibol"){
                aces.forEach((t) => {
                    t.style.display = 'none';
                });
                sets.forEach((i) => {
                    i.style.display = 'flex';
                });
                timer.forEach((j) => {
                    j.style.display = 'none';
                });
                if (sets_a_match) sets_a_match.textContent = match.penalties_a;
                if (sets_b_match) sets_b_match.textContent = match.penalties_b;

                if (namescore) namescore.textContent = "Penaltis";
            }else if(match.detailed == "Finalizada"){
                scorematch.forEach((k) => {
                    k.style.display = 'none';
                });
                if(cvolleyball) cvolleyball.style.display = "none";
                if(cfutsal) cfutsal.style.display = "none";
                if(moments) moments.style.display = "none";
                if(end) end.style.display = "flex";

                const team_end = document.getElementById('end-team-name-b');
                const photo_end = document.getElementById('end-team-photo-b');
                if(match.point_a > match.point_b){
                    if (team_end) team_end.textContent = match.team_name_a;
                    if (photo_end) photo_end.src = match.photoA;
                }else if(match.point_b > match.point_a){
                    if (team_end) team_end.textContent = match.team_name_b;
                    if (photo_end) photo_end.src = match.photoB;                   
                }
                
                // Preencher escalação do vôlei
                preencherEscalacaoVolei(match.players_a, match.players_b);

            }else if(match.detailed == "Escalação" && match.match_sport === "Futsal"){
                scorematch.forEach((k) => {
                    k.style.display = 'none';
                });
                if(cvolleyball) cvolleyball.style.display = "none";
                if(cfutsal) cfutsal.style.display = "flex";
                if(moments) moments.style.display = "none";
                if(end) end.style.display = "none";

                // Parar qualquer ciclo anterior
                if (futsalCycleInterval) {
                    clearInterval(futsalCycleInterval);
                }

                // Salvar os jogadores
                futsalPlayersA = match.players_a;
                futsalPlayersB = match.players_b;

                teamA = match.team_name_a
                teamB = match.team_name_b

                // Começar mostrando o time A (casa)
                currentFutsalTeam = 'a';
                mostrarTimeFutsal(currentFutsalTeam, futsalPlayersA, futsalPlayersB);
                futsalCycleInterval = setInterval(() => {
                    alternarTimeFutsal(futsalPlayersA, futsalPlayersB);
                }, 7000); 

            }else{
                scorematch.forEach((k) => {
                    k.style.display = 'flex';
                });
                if(cvolleyball) cvolleyball.style.display = "none";
                if(cfutsal) cfutsal.style.display = "none";
                if(moments) moments.style.display = "none";
                if(end) end.style.display = "none";
                
                // Parar o ciclo do futsal se estiver ativo
                if (futsalCycleInterval) {
                    clearInterval(futsalCycleInterval);
                    futsalCycleInterval = null;
                }
            }

            stopwatch(match.seconds, match.status)
            break;

        case "point":
            console.log("point");
            const point = data.data;

            const point_a_point = document.getElementById('point-a');
            const point_b_point = document.getElementById('point-b');

            const sets_a_point = document.getElementById('sets-a');
            const sets_b_point = document.getElementById('sets-b');

            const aces_a_point = document.getElementById('aces-a');
            const aces_b_point = document.getElementById('aces-b');

            if (point_a_point) point_a_point.textContent = point.point_a;
            if (point_b_point) point_b_point.textContent = point.point_b;

            if(point.aces_a || point.aces_b){
                if (aces_a_point) aces_a_point.textContent = point.aces_a;
                if (aces_b_point) aces_b_point.textContent = point.aces_b;
            }
            if(point.penalties_a >= 0  || point.penalties_b >= 0){
                if (sets_a_point) sets_a_point.textContent = point.penalties_a;
                if (sets_b_point) sets_b_point.textContent = point.penalties_b;
            }
            if (point.player_name && point.team_name && point.sport === "Futsal" && point.team){
                showGoalCard(
                    point.team,  
                    point.player_name,
                    point.player_img,
                    point.team_img, 
                    point.team_name,
                    point.colorA,
                    point.colorB,
                );
            }
            break;
            
        case "penalties":
            console.log("penalties");
            const penalties = data.data;

            
            const card_a_penalties = document.getElementById('card-a');
            const lack_a_penalties = document.getElementById('lack-a');
            
            const card_b_penalties = document.getElementById('card-b');
            const lack_b_penalties = document.getElementById('lack-b');
            
            const alert_penalties = document.getElementById('alert-penalties');
            const alert_img = document.getElementById('alert-penalties-img');
            const infor_over = document.getElementById('info-overlay');

            if (card_a_penalties) card_a_penalties.textContent = penalties.card_a;
            if (lack_a_penalties) lack_a_penalties.textContent = penalties.lack_a;

            if (card_b_penalties) card_b_penalties.textContent = penalties.card_b;
            if (lack_b_penalties) lack_b_penalties.textContent = penalties.lack_b;

            if (alert_penalties) alert_penalties.textContent = penalties.penalties_player;
            if (alert_img) alert_img.src = penalties.penalties_url;
            if (infor_over) infor_over.style.display = "flex";

            setTimeout(() => {
            if (infor_over) infor_over.style.display = "none";
            }, 8000);

            break;

        case "team":
            console.log("team", data.data);
            const team = data.data;
            const team_a_team = document.getElementById('team-name-a');
            const team_b_team = document.getElementById('team-name-b');
            const photo_a_team = document.getElementById("team-photo-a");
            const photo_b_team = document.getElementById("team-photo-b");

            if(team_a_team) team_a_team.textContent = team.team_name_a;
            if(team_b_team) team_b_team.textContent = team.team_name_b;
            if(photo_a_team) photo_a_team.src = team.photoA;
            if(photo_b_team) photo_b_team.src = team.photoB;

            applyTeamColors(team.colorA, team.colorB);
            
            break;

        case "time":
            console.log("time");
            const time = data.data;

            stopwatch(time.seconds, time.status)

            break;

        case "banner":
            console.log("banner");
            const image = data.data;

            const banner = document.querySelectorAll(".banner-scoreboard");
            const score = document.querySelectorAll('.score-ban');

            if (image.status === 1){
                banner.forEach((i) => {
                    i.style.display = 'flex';
                    i.src = image.banner;
                });
                score.forEach((j) => {
                    j.style.display = 'none';
                });
            }else{
                banner.forEach((i) => {
                    i.style.display = 'none';
                    i.src = "";
                });
                score.forEach((j) => {
                    j.style.display = 'flex';
                });
            }

            break;
        default:
            console.warn("Tipo de mensagem não reconhecido:", data.type);
    }
}

let timeoutId;

function stopwatch(time, stats) {
    console.log(time, stats)
    if (stats == 1) {
        console.log("contando")
        clearTimeout(timeoutId);
        console.log(time, stats)
        var seconds = time;
        seconds++;
        timer.textContent = formatTime(seconds);
        timeoutId = setTimeout(() => stopwatch(seconds, 1), 1000);
    } else if (stats == 2) {
        console.log("Está no status de pausa");
        clearTimeout(timeoutId);
        timer.textContent = formatTime(time);
    } else if (stats == 3) {
        console.log("Está no status de finalizado");
        clearTimeout(timeoutId);
        timer.textContent = formatTime(time);
    }
}

function formatTime(seconds) {
    if (isNaN(seconds)) {
        console.error('Valor inválido para segundos:', seconds);
        return '00:00';
    }

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${hours > 0 ? hours.toString() + ":" : ""}${minutes
        .toString()
        .padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

// Funções para preencher escalações
function preencherEscalacaoVolei(playersA, playersB) {
    // Time A (Casa)
    console.log(playersA);
    console.log(playersB);
    if (playersA && playersA.length >= 6) {
        for (let i = 0; i < 3; i++) {
            const defesaElem = document.getElementById(`casa-defesa-${i+1}`);
            const ataqueElem = document.getElementById(`casa-ataque-${i+1}`);
            
            if (defesaElem && playersA[i]) {
                const img = defesaElem.querySelector('img');
                const nome = defesaElem.querySelector('.jogador-nome');
                img.src = playersA[i].photo_url || '';
                img.alt = playersA[i].name || '';
                nome.textContent = playersA[i].name || '';
                console.log(playersA[i]);
                console.log(playersA[i].photo_url);
            }
            
            if (ataqueElem && playersA[i+3]) {
                const img = ataqueElem.querySelector('img');
                const nome = ataqueElem.querySelector('.jogador-nome');
                img.src = playersA[i+3].photo_url || '';
                img.alt = playersA[i+3].name || '';
                nome.textContent = playersA[i+3].name || '';
            }
        }
    }

    // Time B (Fora)
    if (playersB && playersB.length >= 6) {
        for (let i = 0; i < 3; i++) {
            const ataqueElem = document.getElementById(`fora-ataque-${i+1}`);
            const defesaElem = document.getElementById(`fora-defesa-${i+1}`);
            
            if (ataqueElem && playersB[i]) {
                const img = ataqueElem.querySelector('img');
                const nome = ataqueElem.querySelector('.jogador-nome');
                console.log(playersB[i].photo_url)
                img.src = playersB[i].photo_url || '';
                img.alt = playersB[i].name || '';
                nome.textContent = playersB[i].name || '';
            }
            
            if (defesaElem && playersB[i+3]) {
                const img = defesaElem.querySelector('img');
                const nome = defesaElem.querySelector('.jogador-nome');
                img.src = playersB[i+3].photo_url || '';
                img.alt = playersB[i+3].name || '';
                nome.textContent = playersB[i+3].name || '';
            }
        }
    }
}

// Funções para o ciclo do futsal
function mostrarTimeFutsal(team, futsalPlayersA, futsalPlayersB) {
    console.log(`Mostrando time: ${team}`);
    console.log("eita: 1",futsalPlayersA);
    console.log("eita: 2",futsalPlayersB);
    
    // Primeiro, esconder todos os jogadores
    const todosJogadores = document.querySelectorAll('.quadra-futsal .jogador');
    todosJogadores.forEach(jogador => {
        jogador.style.display = 'none';
    });

    // Mostrar apenas os jogadores do time especificado
    if (team === 'a') {
        const jogadoresTimeA = document.querySelectorAll('.quadra-futsal .time-a');
        jogadoresTimeA.forEach(jogador => {
            jogador.style.display = 'block';
        });
        
        // Preencher dados do time A
        console.log("team a player sformando", futsalPlayersA);
        preencherTimeFutsal('a', futsalPlayersA);
    } else {
        const jogadoresTimeB = document.querySelectorAll('.quadra-futsal .time-b');
        jogadoresTimeB.forEach(jogador => {
            jogador.style.display = 'block';
        });
        
        // Preencher dados do time B
        console.log("team b player sformando", futsalPlayersB);
        preencherTimeFutsal('b', futsalPlayersB);
    }
}

function preencherTimeFutsal(team, players) {
    const funcaoToId = {
        "Goleiro": "goleiro",
        "Fixo": "fixo",
        "Ala 1": "ala1",
        "Ala 2": "ala2",
        "Pivô": "pivo"
    };
    console.log("preencherTimeFutsal",players);
    if (players) {
        players.forEach(player => {
            const idSuffix = funcaoToId[player.funcao];
            if (!idSuffix) return;
            console.log("monatndo uu pô")
            const container = document.getElementById(`${idSuffix}-${team}`);
            if (!container) return;
            console.log("monatndo players pô")

            const img = container.querySelector('img');
            const nome = container.querySelector('.nome');

            img.src = player.photo_url || '';
            img.alt = player.name || '';
            nome.textContent = player.name || '';
        });
    }
}

function alternarTimeFutsal(futsalPlayersA, futsalPlayersB) {
    // Alternar entre time A e B
    currentFutsalTeam = currentFutsalTeam === 'a' ? 'b' : 'a';
    mostrarTimeFutsal(currentFutsalTeam, futsalPlayersA, futsalPlayersB);
    console.log(`Alternando para time: ${currentFutsalTeam === 'a' ? 'Casa' : 'Visitante'}`);
}

// Limpar intervalo quando a página for fechada
window.addEventListener('beforeunload', function() {
    if (futsalCycleInterval) {
        clearInterval(futsalCycleInterval);
    }
});

function isLightColor(color) {
    color = color.replace('#', '');
    const r = parseInt(color.length === 3 ? color[0] + color[0] : color.substr(0, 2), 16);
    const g = parseInt(color.length === 3 ? color[1] + color[1] : color.substr(2, 2), 16);
    const b = parseInt(color.length === 3 ? color[2] + color[2] : color.substr(4, 2), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5;
}

function applyTeamColors(ColorA, ColorB) {
    const teamAContainer = document.getElementById('team-a-container');
    const teamBContainer = document.getElementById('team-b-container');
    
    if (teamAContainer) {
        teamAContainer.style.backgroundColor = ColorA;
        const textColorA = isLightColor(ColorA) ? '#000000' : '#ffffff';
        teamAContainer.style.color = textColorA;
        const titleTeamA = teamAContainer.querySelector('.title-team');
        const scoreTeamA = teamAContainer.querySelector('.score-team');
        if (titleTeamA) titleTeamA.style.color = textColorA;
        if (scoreTeamA) scoreTeamA.style.color = textColorA;
    }
    
    if (teamBContainer) {
        teamBContainer.style.backgroundColor = ColorB;
        const textColorB = isLightColor(ColorB) ? '#000000' : '#ffffff';
        teamBContainer.style.color = textColorB;
        const titleTeamB = teamBContainer.querySelector('.title-team');
        const scoreTeamB = teamBContainer.querySelector('.score-team');
        if (titleTeamB) titleTeamB.style.color = textColorB;
        if (scoreTeamB) scoreTeamB.style.color = textColorB;
    }
    const volleyballTeamA = document.getElementById('volleyball-team-a');
    const volleyballTeamB = document.getElementById('volleyball-team-b');
    
    if (volleyballTeamA) {
        volleyballTeamA.style.color = ColorA;
        volleyballTeamA.style.fontWeight = 'bold';
    }
    
    if (volleyballTeamB) {
        volleyballTeamB.style.color = ColorB;
        volleyballTeamB.style.fontWeight = 'bold';
    }
    const futsalTeamA = document.getElementById('futsal-team-a');
    const futsalTeamB = document.getElementById('futsal-team-b');
    
    if (futsalTeamA) {
        futsalTeamA.style.color = ColorA;
        futsalTeamA.style.fontWeight = 'bold';
    }
    
    if (futsalTeamB) {
        futsalTeamB.style.color = ColorB;
        futsalTeamB.style.fontWeight = 'bold';
    }
    document.documentElement.style.setProperty('--casa-border', ColorA);
    document.documentElement.style.setProperty('--fora-border', ColorB);
}

function showGoalCard(team, playerName, playerImage, teamLogo, teamName, teamColorA, teamColorB) {
    const goalCard = document.getElementById('card-goal');
    const cardHeader = goalCard.querySelector('.card-header');
    const cardFooter = goalCard.querySelector('.card-footer');
    const cornerDecorations = goalCard.querySelectorAll('.corner-decoration');
    const cornerInners = goalCard.querySelectorAll('.corner-inner');
    const imageDecorations = goalCard.querySelectorAll('.image-decoration');
    const primaryColor = team === 'A' ? teamColorA : teamColorB;
    const textColor = isLightColor(primaryColor) ? '#000000' : '#ffffff';
    console.log('--- DISPARANDO GOL ---');
    console.log('Time que marcou:', team);
    console.log('Cor (Time A) recebida do Django:', '"' + teamColorA + '"');
    console.log('Cor (Time B) recebida do Django:', '"' + teamColorB + '"');
    console.log('Cor final escolhida (primaryColor):', '"' + primaryColor + '"');
    goalCard.style.setProperty('--primary-color', primaryColor);
    goalCard.style.setProperty('--text-color', textColor);

    goalCard.style.backgroundColor = primaryColor;
    cardHeader.style.backgroundColor = primaryColor;
    cardHeader.style.color = textColor;
    cardFooter.style.backgroundColor = primaryColor;
    cardFooter.style.color = textColor;

    cornerDecorations.forEach(corner => {
        corner.style.borderColor = primaryColor;
    });
    
    cornerInners.forEach(corner => {
        corner.style.borderColor = textColor;
    });

    const lines = goalCard.querySelectorAll('.line');
    lines.forEach(line => {
        line.style.backgroundColor = textColor;
    });

    imageDecorations.forEach(decoration => {
        decoration.style.backgroundColor = primaryColor;
        decoration.style.opacity = '0.1';
    });

    document.getElementById('card-player-name').textContent = playerName;
    document.getElementById('card-player-name').style.color = textColor;
    document.getElementById('card-team-name').textContent = teamName;
    document.getElementById('card-team-name').style.color = textColor;
    document.getElementById('card-player-img').style.backgroundImage = `url('${playerImage}')`;
    document.getElementById('card-team-img').src = teamLogo;

    const teamImg = document.getElementById('card-team-img');
    teamImg.style.borderColor = textColor;

    goalCard.style.display = 'flex';

    setTimeout(() => {
        goalCard.style.display = 'none';
    }, 5000);
}