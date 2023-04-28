import chess
from chess import WHITE, BLACK, KING, PAWN, BISHOP, QUEEN
import chess.polyglot
import functools
import math
import threading
import time

from const import *
from util import *

print = functools.partial(print, flush=True) # used to fix stdout for UCI


def score_move(board, move, current_depth, pt_best_move = None):
	"""
	Used to score individual moves for move ordering, essentially
	a guess at how likely any given move is to be the correct move
	"""

	score = 0

	if move == pt_best_move:
		# we REALLY prefer to try the best move we found in the previous iteration first before anything else for alpha beta
		return 90000

	attacker = board.piece_at(move.from_square)
	victim = board.piece_at(move.to_square)

	# Promotions, we like to look at them first since they're momentuous moves
	if move.promotion == QUEEN:
		return 80000 + CP_PIECE_VALUES[move.promotion]

	if victim is not None:
		# MVV LVA, we prefer to take the most valuable victim with the least valuable attacker
		return 70000 + CP_PIECE_VALUES[victim.piece_type] - CP_PIECE_VALUES[attacker.piece_type]

	if move in killer_moves[current_depth]:
		return 60000 - killer_moves[current_depth].index(move)

	if len(board.move_stack) and move.to_square == board.move_stack[-1].to_square:
		# a simple, but quite efficient heuristic is capturing the last moved piece
		return 50000

	# Oftentimes if a check is available it will be done, so look at checks earlier
	if board.gives_check(move):
		return 40000

	# Remaining passive moves

	if attacker.piece_type == KING:
		# generally avoid moving king
		score -= CP_PIECE_VALUES[PAWN]
	
	# Change in positional scoring, we would prefer to move from a bad spot to a good spot than a good spot to a bad spot
	score -= MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.from_square if board.turn else chess.square_mirror(move.from_square)]
	score += MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.to_square if board.turn else chess.square_mirror(move.to_square)]
	
	return score


def sorted_moves(moves, board, current_depth, pt_best_move = None):
	"""
	Move Ordering

	In order for alpha beta pruning to be efficient, we want to
	search moves that are the most likely to be best first so
	we can quickly prune out worse lines later on. In order to
	do this, we give each move a score of how likely it is to be
	the best move by quickly moving moves that are obviously bad
	to the bottom of the list and bringing moves that seem good
	at face value to the top to be searched first.
	"""
	
	moves = list(moves)
	moves.sort(key=lambda move: score_move(board, move, current_depth, pt_best_move), reverse=True)
	return moves


def score_board(board):
	"""
	Board Evaluation

	Used to give a best guess of the value of a board at face value without
	doing any tree searches or looking ahead. Simply looking at the board,
	used to evaluate leaf nodes in a tree search. It will miss anything tactical
	but should be able to recognize basic positional advantage and material values.
	"""
	
	if board.is_fivefold_repetition() or board.is_insufficient_material() or board.is_stalemate():
		# Board is drawn
		return 0

	score = 0

	# Check if we are in endgame using the amount of pieces on the board
	endgame = len(board.piece_map()) <= ENDGAME_PIECE_COUNT

	white_bishop_count = 0
	black_bishop_count = 0

	pawn_file_counts = ([0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]) # [turn][file]

	for square, piece in board.piece_map().items(): # Iterate through all pieces on the board
		# Positional piece values, mirror the positional piece values vertically if the piece is black
		if endgame:
			score += ENDGAME_PIECE_POSITION_TABLES[piece.piece_type][square if piece.color == WHITE else chess.square_mirror(square)] * COLOR_MOD[piece.color]
		else:
			score += MIDGAME_PIECE_POSITION_TABLES[piece.piece_type][square if piece.color == WHITE else chess.square_mirror(square)] * COLOR_MOD[piece.color]
		
		score += WILL_TO_PUSH[square if piece.color == WHITE else chess.square_mirror(square)] * COLOR_MOD[piece.color]

		# Piece values, add centipawn values for our pieces, subtract them for opponents pieces
		score += (CP_PIECE_VALUES_ENDGAME[piece.piece_type] if endgame else CP_PIECE_VALUES_MIDGAME[piece.piece_type]) * COLOR_MOD[piece.color]
	
		if piece.piece_type == BISHOP:
			if piece.color == WHITE:
				white_bishop_count += 1
			else:
				black_bishop_count += 1
		
		elif piece.piece_type == PAWN:
			pawn_file_counts[piece.color][chess.square_file(square)] += 1
		
		# Mobility
		score += len(board.attacks(square)) * COLOR_MOD[piece.color]
	
	# Reward having both bishops
	score += (int(white_bishop_count == 2) - int(black_bishop_count == 2)) * DOUBLE_BISHOP_BONUS

	# Doubled / tripled pawn penalties
	for i in range(8):
		score += DOUBLED_PAWN_PENALTY if pawn_file_counts[WHITE][i] == 2 else 0
		score -= DOUBLED_PAWN_PENALTY if pawn_file_counts[BLACK][i] == 2 else 0
		score += TRIPLED_PAWN_PENALTY if pawn_file_counts[WHITE][i] > 2 else 0
		score -= TRIPLED_PAWN_PENALTY if pawn_file_counts[BLACK][i] > 2 else 0

	# We want the score in the current players perspective for negamax to work
	score *= COLOR_MOD[board.turn]

	if not endgame:
		score += TEMPO_BONUS # small bonus for player to move

	return score


## Global Variables ##

# Keep track of how many nodes we've searched and how long we've been searching for UCI info
nodes = 0
search_start_time = 0

# Positional transposition table, dict of {zobrist_hash : flag, leaf_distance, value, board, best_move}
position_table = {}

# Killer move cache, stores beta cutoff moves for move ordering in sibling nodes
killer_moves = []

# Set to true whenever we want to cut off a current search immediately
stop = True


def alpha_beta(board, current_depth, max_depth, alpha, beta, can_null_move=True):
	"""
	Alpha Beta Minimax Search

	This is a negamax implementation of an alpha beta pruned minimax search
	with transposition tables and quiescence search which eventually returns
	the final evaluation of the input board along with the expected line
	"""
	
	if stop:
		return None, None # Immediately return up the stack if stopped
	
	global nodes
	nodes += 1

	alpha_orig = alpha

	score = None

	pv_node = beta - alpha > 1

	# Mate distance pruning
	if current_depth != 0:
		alpha = max(alpha, -CHECKMATE + current_depth)
		beta = min(beta, CHECKMATE - current_depth - 1)

		if alpha >= beta:
			return alpha, board

	pt_hash = chess.polyglot.zobrist_hash(board) # Retrieve entry from the transposition table
	pt_entry = position_table.get(pt_hash)
	
	pt_best_move = None

	# If we have logged this board in the transposition table already, we can load its bounds and make use of them
	if pt_entry is not None:
		if pt_entry["leaf_distance"] >= (max_depth-current_depth) and not pv_node:
			if pt_entry["flag"] == LOWER:
				alpha = max(alpha, pt_entry["value"])
			elif pt_entry["flag"] == UPPER:
				beta = min(beta, pt_entry["value"])
			elif pt_entry["flag"] == EXACT:
				return pt_entry["value"], pt_entry["board"]

			if alpha >= beta:
				return pt_entry["value"], pt_entry["board"]
			
		# This will be used later in move ordering, its generally good to try the best move we found last time
		# first whenever were searching this position again in the future
		pt_best_move = pt_entry["best_move"]
		score = pt_entry["value"]

	if board.is_stalemate() or board.is_insufficient_material() or board.is_fivefold_repetition():
		return 0, board

	# If we've reached our max depth or the game is over, perform a quiescence search
	# If the game is over, the quiescence search will just immediately return the evaluated board anyway
	if current_depth >= max_depth:
		return quiescence(board, max_depth, max_depth, alpha, beta)
	
	futility_prunable = False

	# Keep track of the best board we evaluate so we can return it with its full move stack later
	best_board = board

	if not pv_node and not board.is_check() and not board.is_game_over():
		# Null move reduction
		if can_null_move and current_depth != 0 and (max_depth-current_depth) >= 3:
			if score is None: score = score_board(board)
			nmp_reduction = int(3 + (max_depth-current_depth) / 3 + min((score - beta)/200, 3)) # some magical math that just works

			if nmp_reduction > 0:
				board.push(chess.Move.null())
				score, _ = alpha_beta(board, current_depth + nmp_reduction, max_depth, -beta, -beta+1, can_null_move=False)
				score = -score
				board.pop()
				if score >= beta and not is_mate_score(score):
					return beta, board
		
		# futility pruning
		if (max_depth-current_depth) <= FUTILITY_DEPTH:
			if score is None: score = score_board(board)
			if score + FUTILITY_MARGINS[max_depth-current_depth] < alpha:
				futility_prunable = True

		# reverse futility pruning
		if (max_depth-current_depth) <= REVERSE_FUILITY_DEPTH:
			if score is None: score = score_board(board)
			if score - REVERSE_FUTILTIY_MARGINS[max_depth-current_depth] > beta:
				return score, board

	move_count = 0

	# Iterate through all legal moves sorted
	for move in sorted_moves(board.legal_moves, board, current_depth, pt_best_move=pt_best_move):
		move_count += 1

		is_quiet = is_quiet_move(board, move)

		# Futility pruning
		if futility_prunable and is_quiet and not is_mate_score(alpha) and not is_mate_score(beta):
			continue

		nboard = board.copy() # make a copy of the board and push the move
		nboard.push(move)

		# Late move reduction
		reduction = 0
		if move_count >= (LATE_MOVE_REDUCTION_MOVES + int(pv_node) * 2) and is_quiet and not board.is_check() and not board.gives_check(move) and (max_depth-current_depth) >= LATE_MOVE_REDUCTION_LEAF_DISTANCE:
			reduction = LATE_MOVE_REDUCTION_TABLE[min(max_depth-current_depth, LATE_MOVE_REDUCTION_TABLE_SIZE-1)][min(move_count, LATE_MOVE_REDUCTION_TABLE_SIZE-1)]

		# Principle variance search
		score, end_board = alpha_beta(nboard, current_depth + 1 + reduction, max_depth, -alpha-1, -alpha)
		
		if score is None:
			return None, None
		
		# This is for negamax, which is a minimax framework where we can just negate the score
		# and bounds for each recursive call and it acts as if weve swapped perspectives
		# (both sides will try to maximize now because the rating will be negated whenever it's blacks turn)	
		score = -score

		if (score > alpha) and (score < beta):
			# Evaluate the move by recursively calling alpha beta
			score, end_board = alpha_beta(nboard, current_depth + 1, max_depth, -beta, -alpha)

			if score is None:
				return None, None

			score = -score

		# Alpha beta pruning cutoff, if weve found the opponent can force a move thats
		# worse for us than they can force in a previous board state we analyzed, then
		# we dont need to evaluate this subtree any further because we know they will
		# always play that move thats worse for us, or something even worse
		if score >= beta:
			if is_quiet:
				killer_moves[current_depth].insert(0, move)

			best_board = end_board

			if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
				position_table[pt_hash] = {"flag": LOWER, "leaf_distance": max_depth-current_depth, "value": beta, "board": best_board, "best_move": move}

			return beta, best_board
	
		# Update the lower bound
		if score > alpha:
			alpha = score
			best_board = end_board

	if board.is_game_over():
		score = -CHECKMATE + current_depth if board.is_checkmate() else 0
		if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
			position_table[pt_hash] = {"flag": EXACT, "leaf_distance": max_depth-current_depth, "value": score, "board": board, "best_move": None}
		
		return score, board

	# Update the transposition table with the new information we've learned about this position
	if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
		flag = UPPER if alpha <= alpha_orig else EXACT 
		position_table[pt_hash] = {"flag": flag, "leaf_distance": max_depth-current_depth, "value": alpha, "board": best_board, "best_move": best_board.move_stack[len(board.move_stack)] if len(best_board.move_stack) > len(board.move_stack) else None}

	return alpha, best_board


def quiescence(board, current_depth, max_depth, alpha, beta):
	"""
	Quiescence Search

	This is a light search performed on the leaf nodes of any alpha beta search which
	is meant to bring the board into a "calm" state. We don't want to just evaluate a board
	as neutral using the stateless board evaluation function if there's a big capture for the
	opponent its not taking into account, so first we perform another alpha beta search on only
	capturing moves or checks indefinitely until no more captures or checks are available.
	This means the board is in a calm state and hopefully most tactical lines are analyzed so the
	new leaf nodes we find can be analyzed completely positionally.
	"""

	global nodes
	nodes += 1

	# Get the positional evaluation of the current board
	score = score_board(board)

	# We beta cutoff early in quiescence
	if score >= beta:
		return beta, board

	alpha = max(alpha, score)

	# Filter moves to only be "loud" moves including captures, promotions or checks
	# We only search checks up to a certain depth to avoid searching check repetitions
	# We only really care about tactical checks anyway like forks or discovered checks, etc.
	sorted_quiesence_moves = sorted_moves(
		(move for move in board.legal_moves if not is_quiet_move(board, move, quiescence_depth=current_depth-max_depth)),
		board,
		current_depth
	)

	best_board = board

	# Same as the alpha beta negamax search
	for move in sorted_quiesence_moves:
		nboard = board.copy()
		nboard.push(move)

		score, end_board = quiescence(nboard, current_depth+1, max_depth, -beta, -alpha)
		score = -score

		if score >= beta:
			return beta, end_board

		if score > alpha:
			alpha = score
			best_board = end_board

	return alpha, best_board


def info_loop():
	"""
	Info Loop

	This is just a basic loop that runs in a separate thread to report nodes per
	second and some other info for UCI. It also handles limited movetime stop signals
	but I'll probably move that out of here eventually
	"""

	global stop
	start = time.time()
	offset = 0

	n = 0
	while not stop:
		time.sleep(0.01)

		if allowed_movetime is not None and int((time.time()-search_start_time) * 1000) >= allowed_movetime:
			stop = True

		if n % 25 == 0:
			end = time.time()
			nps = (nodes-offset) / (end - start)
			offset = nodes
			start = time.time()
			with threading.Lock():
				print(f"info nodes {nodes} nps {int(nps)} time {int((time.time()-search_start_time) * 1000)} hashfull {int(len(position_table) / MAX_PTABLE_SIZE * 1000)}")
		
		n += 1

def iterative_deepening(board):
	"""
	Iterative Deepening

	Basic principal of searching depth 1, then depth 2, 3 ... and so on
	If we run out of time we can always just fall back on the last depth
	we've fully searched. This also implements aspiration windows, where
	we first search a tight bound around a guess of the rating (which we
	just set to be the evaluation of the last depth) expecting that the
	evaluation will generally not change much between depths. If it does,
	then we detect that the search has failed outside of our tight bound
	and we have to widen the bound and do a costly research. The default
	aspiration window size and growth rates can be tuned to give the best
	performance from this technique.
	"""

	# We're starting a search so reset some variables
	global stop
	global nodes
	global search_start_time
	global killer_moves

	search_start_time = time.time()
	stop = False
	nodes = 0
	depth = STARTING_DEPTH
	bestmove = None

	# Clear the transposition table
	position_table.clear()

	# Fill killer moves cache with None
	killer_moves = [[] for _ in range(MAX_DEPTH)]

	# This is our first aspiration window guess, before we search depth 1
	gamma = score_board(board)

	# Iterative deepening
	while not stop and depth < MAX_DEPTH:
		aspw_lower = -ASPIRATION_WINDOW_DEFAULT
		aspw_higher = ASPIRATION_WINDOW_DEFAULT

		if depth >= ASPIRATION_WINDOW_DEPTH:
			while True:
				# We set our bounds to be the size of our aspiration window around our guess (gamma)
				alpha = gamma + aspw_lower
				beta = gamma + aspw_higher

				# Perform the alpha beta search
				score, end_board = alpha_beta(board, 0, depth, alpha, beta)

				# If this happens it means we stopped mid search so just end the search
				if score is None:
					break

				# Our next aspiration table guess is the value we gave the board at this depth
				# because we would expect it shouldn't change too much in the next depth	
				gamma = score

				# If we end up outside the aspiration window bounds, we need to make them wider and re search
				if score <= alpha:
					print(score, "low cut")
					aspw_lower *= ASPIRATION_INCREASE_EXPONENT
				elif score >= beta:
					print(score, "high cut")
					aspw_higher *= ASPIRATION_INCREASE_EXPONENT
				else:
					# If were inside the bounds, then we can proceed to the next depth
					break
				
		else:
			score, end_board = alpha_beta(board, 0, depth, -CHECKMATE, CHECKMATE)
			gamma = score


		# UCI reporting
		if score is not None:
			depth_string = f"depth {depth} seldepth {len(end_board.move_stack) - len(board.move_stack)}" # full search depth / quiescence search depth
			time_string = f"time {int((time.time()-search_start_time) * 1000)}" # time spent searching this position
			hashfull_string = f"hashfull {int(len(position_table) / MAX_PTABLE_SIZE * 1000)}" # how full the transposition table is
			pv_string = f"pv {' '.join([str(move) for move in end_board.move_stack[len(board.move_stack):]])}" # move preview
			bestmove = end_board.move_stack[len(board.move_stack)]

			if is_mate_score(score):
				# Checkmate is found, report how many moves its in
				mate_in = math.ceil((abs(CHECKMATE)-abs(score)) / 2) * COLOR_MOD[score > 0]
				with threading.Lock(): print(f"info nodes {nodes} {time_string} {hashfull_string} {depth_string} score mate {mate_in} {pv_string}")
			else:
				# Otherwise just report centipawns score
				with threading.Lock(): print(f"info nodes {nodes} {time_string} {hashfull_string} {depth_string} score cp {score} {pv_string}")

			# Prepare for the next search
			depth += 1
	
	if bestmove:
		# When we end our search (due to stop command or running out of time), report the best move we found
		print(f"bestmove {bestmove.uci()}")


# The board used by UCI commands
board = chess.Board()

# Threads
search_thread = None
node_info_thread = None

while True:
	# UCI implementation
	line = input()
	args = line.split()
	cmd = args[0] if len(args) else None

	if cmd == "uci":
		print(f"id name {VERSION}")
		print(f"id author {AUTHOR}")
		print("uciok")
	
	elif cmd == "isready":
		print("readyok")
	
	elif cmd == "quit":
		stop = True
		break

	elif cmd == "position":
		if "fen" in args: # load position from FEN
			fen = line.split(" fen ")[1].split("moves")[0]
			board = chess.Board(fen=fen)
		
		elif "startpos" in args: # standard chess starting position
			board = chess.Board()
			
		if "moves" in args: # load position from list of moves
			moves = line.split(" moves ")[1].split()
			for move in moves:
				board.push(chess.Move.from_uci(move))
			
	elif cmd == "go":
		if "movetime" in args:
			allowed_movetime = int(args[args.index("movetime")+1])
		else:
			allowed_movetime = None
		
		if stop:
			# Begin our search by starting up the threads
			search_thread = threading.Thread(target=lambda: iterative_deepening(board), daemon=True)
			node_info_thread = threading.Thread(target=lambda: info_loop(), daemon=True)
			search_thread.start()
			node_info_thread.start()

	elif cmd == "stop":
		if not stop:
			stop = True
			while search_thread.is_alive() or node_info_thread.is_alive():
				# Wait for threads to recieve stop signal before proceeding
				pass
