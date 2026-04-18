let board = null;
let isThinking = false;
let selectedSquare = null;
let currentFen = "start";
let isTouchDevice = window.matchMedia("(pointer: coarse)").matches;

function updateStatus(text) {
    document.getElementById("status").textContent = text;
}

function updateLastMove(text) {
    document.getElementById("lastMove").textContent = "Dernier coup : " + text;
}

function updateResult(text) {
    document.getElementById("result").textContent = text || "";
}

function updateEval(text) {
    document.getElementById("eval").textContent = "Évaluation : " + text;
}

function updateThinking(text) {
    document.getElementById("thinking").textContent = "Temps IA : " + text;
}

function updateHistory(moveStack) {
    const historyDiv = document.getElementById("history");

    if (!moveStack || moveStack.length === 0) {
        historyDiv.textContent = "-";
        return;
    }

    let formatted = "";
    for (let i = 0; i < moveStack.length; i += 2) {
        const whiteMove = moveStack[i] || "";
        const blackMove = moveStack[i + 1] || "";
        formatted += `${Math.floor(i / 2) + 1}. ${whiteMove} ${blackMove}\n`;
    }

    historyDiv.textContent = formatted;
}

function setControlsDisabled(disabled) {
    document.getElementById("depthSelect").disabled = disabled;
    document.getElementById("resetBtn").disabled = disabled;
}

function clearSquareHighlights() {
    document.querySelectorAll(".square-55d63").forEach(square => {
        square.classList.remove("square-selected");
    });
}

function highlightSquare(squareName) {
    clearSquareHighlights();
    const squareEl = document.querySelector(`.square-${squareName}`);
    if (squareEl) {
        squareEl.classList.add("square-selected");
    }
}

function clearSelection() {
    selectedSquare = null;
    clearSquareHighlights();
}

function getSquareNameFromElement(squareEl) {
    const classes = Array.from(squareEl.classList);
    const squareClass = classes.find(c => c.startsWith("square-") && c !== "square-55d63");
    return squareClass ? squareClass.replace("square-", "") : null;
}

function getPieceCodeOnSquare(squareName) {
    const squareEl = document.querySelector(`.square-${squareName}`);
    if (!squareEl) return null;

    const pieceEl = squareEl.querySelector(".piece-417db");
    if (!pieceEl) return null;

    return pieceEl.getAttribute("data-piece");
}

function isWhitePieceOnSquare(squareName) {
    const piece = getPieceCodeOnSquare(squareName);
    return piece && piece.startsWith("w");
}

function loadState() {
    fetch("/state")
        .then(response => response.json())
        .then(data => {
            currentFen = data.fen;

            if (board) {
                board.position(data.fen, false);
                board.resize();
            }

            updateHistory(data.move_stack);

            if (data.is_game_over) {
                updateStatus("Partie terminée");
                updateResult("Résultat : " + data.result);
            } else {
                updateStatus("À vous de jouer");
                updateResult("");
            }

            clearSelection();
        })
        .catch(error => {
            updateStatus("Erreur chargement état.");
            console.error("Erreur /state :", error);
        });
}

function applyAiMove(aiMoveUci) {
    if (!aiMoveUci || aiMoveUci.length < 4 || !board) return;

    const from = aiMoveUci.slice(0, 2);
    const to = aiMoveUci.slice(2, 4);
    board.move(`${from}-${to}`);
}

function sendMove(move, fallbackPosition = null) {
    if (isThinking) return;

    const depth = document.getElementById("depthSelect").value;

    // Affichage immédiat du coup du joueur
    if (board && move.length >= 4) {
        const from = move.slice(0, 2);
        const to = move.slice(2, 4);
        board.move(`${from}-${to}`);
        board.resize();
    }

    isThinking = true;
    setControlsDisabled(true);
    updateStatus("L'IA réfléchit...");
    clearSelection();

    fetch("/move", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            move: move,
            depth: depth
        })
    })
        .then(response => response.json())
        .then(data => {
            isThinking = false;
            setControlsDisabled(false);

            if (!data.ok) {
                updateStatus(data.error || "Erreur inconnue.");

                // On remet la position précédente si le coup échoue
                if (fallbackPosition && board) {
                    board.position(fallbackPosition, false);
                    board.resize();
                } else {
                    loadState();
                }
                return;
            }

            let moveText = data.player_move || "-";
            if (data.ai_move) {
                moveText += " | IA : " + data.ai_move;
            }

            updateLastMove(moveText);
            updateHistory(data.move_stack);

            if (data.evaluation !== null && data.evaluation !== undefined) {
                updateEval((data.evaluation / 100).toFixed(2));
            } else {
                updateEval("-");
            }

            if (data.thinking_time !== null && data.thinking_time !== undefined) {
                updateThinking(data.thinking_time + " s");
            } else {
                updateThinking("-");
            }

            if (data.ai_move) {
                setTimeout(() => {
                    applyAiMove(data.ai_move);

                    setTimeout(() => {
                        loadState();
                    }, 250);
                }, 150);
            } else {
                loadState();
            }

            if (data.is_game_over) {
                updateStatus("Partie terminée");
                updateResult("Résultat : " + data.result);
            } else if (data.is_check) {
                updateStatus("Échec !");
                updateResult("");
            } else {
                updateStatus("À vous de jouer");
                updateResult("");
            }
        })
        .catch(error => {
            isThinking = false;
            setControlsDisabled(false);
            updateStatus("Erreur réseau ou serveur.");
            console.error("Erreur /move :", error);

            // On remet la position précédente en cas d'erreur
            if (fallbackPosition && board) {
                board.position(fallbackPosition, false);
                board.resize();
            } else {
                loadState();
            }
        });
}

function buildMove(fromSquare, toSquare) {
    let move = fromSquare + toSquare;

    // Promotion auto en dame
    if (fromSquare[1] === "7" && toSquare[1] === "8") {
        move += "q";
    }

    return move;
}

function handleTapSquare(squareName) {
    if (isThinking) return;

    if (!selectedSquare) {
        if (isWhitePieceOnSquare(squareName)) {
            selectedSquare = squareName;
            highlightSquare(squareName);
        }
        return;
    }

    if (selectedSquare === squareName) {
        clearSelection();
        return;
    }

    // Si on retape une autre pièce blanche, on change la sélection
    if (isWhitePieceOnSquare(squareName)) {
        selectedSquare = squareName;
        highlightSquare(squareName);
        return;
    }

    const move = buildMove(selectedSquare, squareName);
    sendMove(move, currentFen);
}

function setupTapToMove() {
    const boardEl = document.getElementById("board");

    boardEl.addEventListener("click", function (event) {
        if (!isTouchDevice) return;

        const squareEl = event.target.closest(".square-55d63");
        if (!squareEl) return;

        const squareName = getSquareNameFromElement(squareEl);
        if (!squareName) return;

        handleTapSquare(squareName);
    });

    boardEl.addEventListener("touchend", function (event) {
        if (!isTouchDevice) return;

        const touch = event.changedTouches[0];
        const target = document.elementFromPoint(touch.clientX, touch.clientY);
        if (!target) return;

        const squareEl = target.closest(".square-55d63");
        if (!squareEl) return;

        event.preventDefault();

        const squareName = getSquareNameFromElement(squareEl);
        if (!squareName) return;

        handleTapSquare(squareName);
    }, { passive: false });
}

function onDragStart(source, piece) {
    if (isTouchDevice) return false; // sur mobile on force le click-click
    if (isThinking) return false;
    if (document.getElementById("result").textContent !== "") return false;
    if (piece.search(/^b/) !== -1) return false;
    return true;
}

function onDrop(source, target, piece, newPos, oldPos) {
    if (isTouchDevice) return "snapback";
    if (isThinking) return "snapback";
    if (source === target) return "snapback";

    let move = source + target;

    if (piece === "wP" && target[1] === "8") move += "q";
    if (piece === "bP" && target[1] === "1") move += "q";

    sendMove(move, oldPos);
}

function initializeBoard() {
    board = Chessboard("board", {
        position: "start",
        draggable: !isTouchDevice,
        showErrors: "console",
        pieceTheme: "https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png",
        onDragStart: onDragStart,
        onDrop: onDrop
    });

    setTimeout(() => {
        if (board) board.resize();
    }, 150);

    window.addEventListener("resize", function () {
        if (board) board.resize();
    });
}

document.addEventListener("DOMContentLoaded", function () {
    initializeBoard();
    setupTapToMove();
    loadState();

    document.getElementById("resetBtn").addEventListener("click", function () {
        if (isThinking) return;

        fetch("/reset", {
            method: "POST"
        })
            .then(response => response.json())
            .then(data => {
                currentFen = data.fen;

                if (board) {
                    board.position(data.fen, false);
                    board.resize();
                }

                updateStatus("Nouvelle partie");
                updateLastMove("-");
                updateEval("-");
                updateThinking("-");
                updateResult("");
                updateHistory(data.move_stack);
                clearSelection();
            })
            .catch(error => {
                updateStatus("Erreur reset.");
                console.error("Erreur /reset :", error);
            });
    });
});