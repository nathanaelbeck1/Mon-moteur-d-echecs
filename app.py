from flask import Flask, render_template, request, jsonify
import chess
import time
import random

app = Flask(__name__)

board = chess.Board()

INF = 10**9
MATE_SCORE = 100000

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

PAWN_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0
]

KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
]

ROOK_TABLE = [
     0,   0,   5,  10,  10,   5,   0,   0,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     5,  10,  10,  10,  10,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0
]

QUEEN_TABLE = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
      0,   0,   5,   5,   5,   5,   0,  -5,
     -5,   0,   5,   5,   5,   5,   0,  -5,
    -10,   0,   5,   5,   5,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
]

KING_MID_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20
]

KING_END_TABLE = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}

TRANSPOSITION_TABLE = {}


def is_endgame(current_board):
    queens = (
        len(current_board.pieces(chess.QUEEN, chess.WHITE)) +
        len(current_board.pieces(chess.QUEEN, chess.BLACK))
    )

    minor_rook_material = 0
    for piece_type in [chess.ROOK, chess.BISHOP, chess.KNIGHT]:
        minor_rook_material += len(current_board.pieces(piece_type, chess.WHITE))
        minor_rook_material += len(current_board.pieces(piece_type, chess.BLACK))

    return queens == 0 or (queens == 2 and minor_rook_material <= 2)


def piece_square_value(piece, square, current_board):
    idx = square if piece.color == chess.WHITE else chess.square_mirror(square)

    if piece.piece_type == chess.KING:
        table = KING_END_TABLE if is_endgame(current_board) else KING_MID_TABLE
        return table[idx]

    table = PIECE_SQUARE_TABLES.get(piece.piece_type)
    return table[idx] if table else 0


def development_score(current_board):
    score = 0

    white_start_squares = {
        chess.B1: chess.KNIGHT,
        chess.G1: chess.KNIGHT,
        chess.C1: chess.BISHOP,
        chess.F1: chess.BISHOP
    }

    black_start_squares = {
        chess.B8: chess.KNIGHT,
        chess.G8: chess.KNIGHT,
        chess.C8: chess.BISHOP,
        chess.F8: chess.BISHOP
    }

    for sq, piece_type in white_start_squares.items():
        piece = current_board.piece_at(sq)
        if piece is None or piece.color != chess.WHITE or piece.piece_type != piece_type:
            score += 15

    for sq, piece_type in black_start_squares.items():
        piece = current_board.piece_at(sq)
        if piece is None or piece.color != chess.BLACK or piece.piece_type != piece_type:
            score -= 15

    return score


def center_control_score(current_board):
    score = 0
    center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

    for sq in center_squares:
        attackers_white = len(current_board.attackers(chess.WHITE, sq))
        attackers_black = len(current_board.attackers(chess.BLACK, sq))
        score += 12 * (attackers_white - attackers_black)

    return score


def rook_penalty_score(current_board):
    score = 0

    if is_endgame(current_board):
        return 0

    for sq in current_board.pieces(chess.ROOK, chess.WHITE):
        if sq not in [chess.A1, chess.H1]:
            score -= 10

    for sq in current_board.pieces(chess.ROOK, chess.BLACK):
        if sq not in [chess.A8, chess.H8]:
            score += 10

    return score


def king_safety_score(current_board):
    score = 0

    white_king_sq = current_board.king(chess.WHITE)
    black_king_sq = current_board.king(chess.BLACK)

    if white_king_sq in [chess.G1, chess.C1]:
        score += 40
    elif white_king_sq == chess.E1 and not is_endgame(current_board):
        score -= 25

    if black_king_sq in [chess.G8, chess.C8]:
        score -= 40
    elif black_king_sq == chess.E8 and not is_endgame(current_board):
        score += 25

    return score


def pawn_structure_score(current_board):
    score = 0

    for color in [chess.WHITE, chess.BLACK]:
        pawns = list(current_board.pieces(chess.PAWN, color))
        files = [chess.square_file(sq) for sq in pawns]

        for file_idx in range(8):
            count = files.count(file_idx)
            if count > 1:
                penalty = 12 * (count - 1)
                score += -penalty if color == chess.WHITE else penalty

        for sq in pawns:
            file_idx = chess.square_file(sq)
            has_left = (file_idx - 1) in files
            has_right = (file_idx + 1) in files
            if not has_left and not has_right:
                score += -10 if color == chess.WHITE else 10

        opponent_pawns = list(current_board.pieces(chess.PAWN, not color))
        for sq in pawns:
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)

            blocked = False
            for op_sq in opponent_pawns:
                op_file = chess.square_file(op_sq)
                op_rank = chess.square_rank(op_sq)

                if abs(op_file - file_idx) <= 1:
                    if color == chess.WHITE and op_rank > rank_idx:
                        blocked = True
                    elif color == chess.BLACK and op_rank < rank_idx:
                        blocked = True

            if not blocked:
                bonus = 20
                score += bonus if color == chess.WHITE else -bonus

    return score


def evaluate_board(current_board):
    if current_board.is_checkmate():
        return -MATE_SCORE if current_board.turn == chess.WHITE else MATE_SCORE

    if (
        current_board.is_stalemate()
        or current_board.is_insufficient_material()
        or current_board.can_claim_draw()
    ):
        return 0

    score = 0

    for square, piece in current_board.piece_map().items():
        value = PIECE_VALUES[piece.piece_type]
        value += piece_square_value(piece, square, current_board)

        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value

    if len(current_board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 30
    if len(current_board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= 30

    turn_backup = current_board.turn

    current_board.turn = chess.WHITE
    white_mobility = current_board.legal_moves.count()

    current_board.turn = chess.BLACK
    black_mobility = current_board.legal_moves.count()

    current_board.turn = turn_backup
    score += 4 * (white_mobility - black_mobility)

    score += center_control_score(current_board)
    score += development_score(current_board)
    score += king_safety_score(current_board)
    score += rook_penalty_score(current_board)
    score += pawn_structure_score(current_board)

    if current_board.is_check():
        score += -40 if current_board.turn == chess.WHITE else 40

    if current_board.is_repetition(2):
        score += -25 if current_board.turn == chess.WHITE else 25

    return score


def evaluate_for_side_to_move(current_board):
    eval_white = evaluate_board(current_board)
    return eval_white if current_board.turn == chess.WHITE else -eval_white


def move_ordering_score(current_board, move):
    score = 0

    if move.promotion:
        score += 800 + PIECE_VALUES.get(move.promotion, 0)

    if current_board.is_capture(move):
        victim_piece = current_board.piece_at(move.to_square)
        attacker_piece = current_board.piece_at(move.from_square)

        if victim_piece is None and current_board.is_en_passant(move):
            victim_value = PIECE_VALUES[chess.PAWN]
        else:
            victim_value = PIECE_VALUES[victim_piece.piece_type] if victim_piece else 0

        attacker_value = PIECE_VALUES[attacker_piece.piece_type] if attacker_piece else 0
        score += 10 * victim_value - attacker_value + 1000

    if current_board.gives_check(move):
        score += 150

    to_sq = move.to_square
    center_bonus = 3 - abs(chess.square_file(to_sq) - 3.5) - abs(chess.square_rank(to_sq) - 3.5)
    score += int(center_bonus * 10)

    return score


def ordered_moves(current_board, tactical_only=False):
    moves = list(current_board.legal_moves)

    if tactical_only:
        moves = [
            m for m in moves
            if current_board.is_capture(m) or m.promotion or current_board.gives_check(m)
        ]

    moves.sort(key=lambda m: move_ordering_score(current_board, m), reverse=True)
    return moves


def quiescence(current_board, alpha, beta):
    stand_pat = evaluate_for_side_to_move(current_board)

    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in ordered_moves(current_board, tactical_only=True):
        current_board.push(move)
        score = -quiescence(current_board, -beta, -alpha)
        current_board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def negamax(current_board, depth, alpha, beta):
    key = current_board.fen()

    if key in TRANSPOSITION_TABLE:
        stored_depth, stored_score = TRANSPOSITION_TABLE[key]
        if stored_depth >= depth:
            return stored_score

    if current_board.is_game_over():
        if current_board.is_checkmate():
            return -MATE_SCORE + (10 - depth)
        return 0

    if depth == 0:
        return quiescence(current_board, alpha, beta)

    max_score = -INF

    for move in ordered_moves(current_board):
        current_board.push(move)
        score = -negamax(current_board, depth - 1, -beta, -alpha)
        current_board.pop()

        if score > max_score:
            max_score = score
        if score > alpha:
            alpha = score
        if alpha >= beta:
            break

    TRANSPOSITION_TABLE[key] = (depth, max_score)
    return max_score


def get_best_move(current_board, depth=3):
    best_moves = []
    best_score = -INF

    moves = ordered_moves(current_board)
    if not moves:
        return None, 0

    for move in moves:
        current_board.push(move)
        score = -negamax(current_board, depth - 1, -INF, INF)
        current_board.pop()

        if score > best_score:
            best_score = score
            best_moves = [move]
        elif abs(score - best_score) <= 10:
            best_moves.append(move)

    if not best_moves:
        return None, 0

    return random.choice(best_moves), best_score


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/state", methods=["GET"])
def state():
    return jsonify({
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "is_game_over": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
        "move_stack": [move.uci() for move in board.move_stack]
    })


@app.route("/move", methods=["POST"])
def move():
    global board

    data = request.get_json()

    if not data or "move" not in data:
        return jsonify({"ok": False, "error": "Aucun coup reçu."}), 400

    move_uci = data.get("move", "").strip()
    depth = int(data.get("depth", 3))

    try:
        move_obj = chess.Move.from_uci(move_uci)
    except Exception:
        return jsonify({"ok": False, "error": f"Coup invalide : {move_uci}"}), 400

    if move_obj not in board.legal_moves:
        return jsonify({"ok": False, "error": f"Coup illégal : {move_uci}"}), 400

    try:
        # Coup du joueur
        board.push(move_obj)
        player_move = move_obj.uci()

        ai_move_uci = None
        ai_eval = None
        thinking_time = 0.0

        if not board.is_game_over():
            TRANSPOSITION_TABLE.clear()
            start = time.time()
            ai_move, ai_eval = get_best_move(board, depth=depth)
            thinking_time = round(time.time() - start, 2)

            if ai_move:
                ai_move_uci = ai_move.uci()
                board.push(ai_move)

        return jsonify({
            "ok": True,
            "fen": board.fen(),
            "player_move": player_move,
            "ai_move": ai_move_uci,
            "evaluation": ai_eval,
            "thinking_time": thinking_time,
            "turn": "white" if board.turn == chess.WHITE else "black",
            "is_game_over": board.is_game_over(),
            "result": board.result() if board.is_game_over() else None,
            "is_check": board.is_check(),
            "move_stack": [m.uci() for m in board.move_stack]
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"Erreur moteur : {str(e)}"}), 500


@app.route("/reset", methods=["POST"])
def reset():
    global board
    board = chess.Board()
    TRANSPOSITION_TABLE.clear()

    return jsonify({
        "ok": True,
        "fen": board.fen(),
        "turn": "white",
        "is_game_over": False,
        "result": None,
        "move_stack": []
    })

if __name__ == "__main__":
    app.run(debug=True)