import chess
from chess import WHITE, BLACK, KING, PAWN, BISHOP, KNIGHT, ROOK, QUEEN
import chess.polyglot
import functools
import math
import threading
import time

from const import *
from util import *

print = functools.partial(print, flush=True) # used to fix stdout for UCI


def score_move(board, move, current_depth, phase, pt_best_move = None):
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
		return 80000

	if victim is not None:
		# MVV LVA, we prefer to take the most valuable victim with the least valuable attacker
		return 70000 + lerp(PHASED_CP_PIECE_VALUES[MIDGAME][victim.piece_type], PHASED_CP_PIECE_VALUES[ENDGAME][victim.piece_type], phase) - lerp(PHASED_CP_PIECE_VALUES[MIDGAME][attacker.piece_type], PHASED_CP_PIECE_VALUES[MIDGAME][attacker.piece_type], phase)

	if move in killer_moves[current_depth]:
		return 60000 - killer_moves[current_depth].index(move)

	if len(board.move_stack) >= 2 and move == countermove_table[board.move_stack[-2].from_square][board.move_stack[-2].to_square]:
		return 50000

	if len(board.move_stack) and move.to_square == board.move_stack[-1].to_square:
		# a simple, but quite efficient heuristic is capturing the last moved piece
		return 40000

	# Oftentimes if a check is available it will be done, so look at checks earlier
	if board.gives_check(move):
		return 30000

	score += history_table[board.turn][move.from_square][move.to_square]

	# Remaining passive moves

	if attacker.piece_type == KING:
		# generally avoid moving king
		score -= CP_PIECE_VALUES[PAWN]
	
	# Change in positional scoring, we would prefer to move from a bad spot to a good spot than a good spot to a bad spot
	score -= lerp(
		MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.from_square if board.turn else chess.square_mirror(move.from_square)],
		ENDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.from_square if board.turn else chess.square_mirror(move.from_square)],
		phase
	)

	score += lerp(
		MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.to_square if board.turn else chess.square_mirror(move.to_square)],
		ENDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.to_square if board.turn else chess.square_mirror(move.to_square)],
		phase
	)
	
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
	
	phase = game_phase(board)

	moves = list(moves)
	moves.sort(key=lambda move: score_move(board, move, current_depth, phase, pt_best_move), reverse=True)
	return moves


def game_phase(board): # returns a float from 0-1 representing game phase
	remaining = 0
	remaining += len(board.pieces(PAWN, BLACK) | board.pieces(PAWN, WHITE))
	remaining += len(board.pieces(KNIGHT, BLACK) | board.pieces(KNIGHT, WHITE)) * 10
	remaining += len(board.pieces(BISHOP, BLACK) | board.pieces(BISHOP, WHITE)) * 10
	remaining += len(board.pieces(ROOK, BLACK) | board.pieces(ROOK, WHITE)) * 20
	remaining += len(board.pieces(QUEEN, BLACK) | board.pieces(QUEEN, WHITE)) * 40

	return max(0, min(1, (256-remaining)/256))


def score_board(board):
	"""
	Board Evaluation

	Used to give a best guess of the value of a board at face value without
	doing any tree searches or looking ahead. Simply looking at the board,
	used to evaluate leaf nodes in a tree search. It will miss anything tactical
	but should be able to recognize basic positional advantage and material values.
	"""
	
	if board.can_claim_draw() or board.is_insufficient_material() or board.is_stalemate():
		# Board is drawn
		return 0

	score = 0

	# Check if we are in endgame using the amount of pieces on the board
	phase = game_phase(board)

	pawn_file_counts = ([0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]) # [turn][file]

	for square in range(64): # Iterate through all pieces on the board
		# Positional piece values, mirror the positional piece values vertically if the piece is black
		piece_type = board.piece_type_at(square)

		if piece_type is not None:
			piece_color = board.color_at(square)
			color_mod = COLOR_MOD[piece_color]

			pov_square = square if piece_color == WHITE else chess.square_mirror(square)

			score += lerp(
				MIDGAME_PIECE_POSITION_TABLES[piece_type][pov_square],
				ENDGAME_PIECE_POSITION_TABLES[piece_type][pov_square],
				phase
			) * color_mod

			score += chess.square_rank(pov_square) * WILL_TO_PUSH * color_mod

			# Piece values, add centipawn values for our pieces, subtract them for opponents pieces
			score += lerp(PHASED_CP_PIECE_VALUES[MIDGAME][piece_type], PHASED_CP_PIECE_VALUES[ENDGAME][piece_type], phase) * color_mod

			if piece_type == PAWN:
				pawn_file_counts[piece_color][chess.square_file(square)] += 1

			score += lerp(
				PIECE_MOBILITY_TABLES[piece_type][MIDGAME][len(board.attacks(square))], # midgame
				PIECE_MOBILITY_TABLES[piece_type][ENDGAME][len(board.attacks(square))], # endgame
				phase
			) * color_mod

	# Reward having both bishops
	dbb = lerp(DOUBLE_BISHOP_BONUS[MIDGAME], DOUBLE_BISHOP_BONUS[ENDGAME], phase)
	score += (dbb if len(board.pieces(BISHOP, WHITE)) == 2 else 0) - (dbb if len(board.pieces(BISHOP, BLACK)) == 2 else 0)

	# pawn structure basics
	for i in range(8):
		# doubled / tripled pawn penalties
		dpp = lerp(DOUBLED_PAWN_PENALTY[MIDGAME], DOUBLED_PAWN_PENALTY[ENDGAME], phase)
		tpp = lerp(DOUBLED_PAWN_PENALTY[MIDGAME], DOUBLED_PAWN_PENALTY[ENDGAME], phase)
		ipp = lerp(ISOLATED_PAWN_PENALTY[MIDGAME], ISOLATED_PAWN_PENALTY[ENDGAME], phase)

		score += (dpp if pawn_file_counts[WHITE][i] == 2 else 0) - (dpp if pawn_file_counts[BLACK][i] == 2 else 0)
		score += (tpp if pawn_file_counts[WHITE][i] > 2 else 0) - (tpp if pawn_file_counts[BLACK][i] > 2 else 0)

		# isolated pawn penalties
		if pawn_file_counts[WHITE][i] > 0 and (i == 0 or pawn_file_counts[WHITE][i-1] == 0) and (i == 7 or pawn_file_counts[WHITE][i+1] == 0):
			score += ipp
		
		if pawn_file_counts[BLACK][i] > 0 and (i == 0 or pawn_file_counts[BLACK][i-1] == 0) and (i == 7 or pawn_file_counts[BLACK][i+1] == 0):
			score -= ipp

	# We want the score in the current players perspective for negamax to work
	score *= COLOR_MOD[board.turn]

	score += lerp(TEMPO_BONUS[MIDGAME], TEMPO_BONUS[ENDGAME], phase) # small bonus for player to move

	return score


## Global Variables ##

# Keep track of how many nodes we've searched and how long we've been searching for UCI info
nodes = 0
search_start_time = 0

# Positional transposition table, dict of {zobrist_hash : flag, leaf_distance, value, board, best_move}
position_table = {}

# Killer move cache, stores beta cutoff moves for move ordering in sibling nodes
killer_moves = []

# Refutation move cache
countermove_table = []

# History heuristic table
history_table = []

# Set to true whenever we want to cut off a current search immediately
stop = True

# Selective depth
seldepth = 0


def alpha_beta(board, current_depth, max_depth, alpha, beta, can_null_move=True):
	"""
	Alpha Beta Minimax Search

	This is a negamax implementation of an alpha beta pruned minimax search
	with transposition tables and quiescence search which eventually returns
	the final evaluation of the input board along with the expected line
	"""
	
	if halted():
		return # Immediately return up the stack if stopped
	
	global nodes
	nodes += 1

	alpha_orig = alpha

	score = None

	game_over = board.is_game_over()

	pv_node = beta - alpha > 1

	# Mate distance pruning
	if current_depth != 0:
		alpha = max(alpha, -CHECKMATE + current_depth)
		beta = min(beta, CHECKMATE - current_depth - 1)

		if alpha >= beta:
			return alpha

	pt_hash = chess.polyglot.zobrist_hash(board) # Retrieve entry from the transposition table
	pt_entry = position_table.get(pt_hash)
	
	pt_best_move = None

	# If we have logged this board in the transposition table already, we can load its bounds and make use of them
	if pt_entry is not None:
		if pt_entry[LEAF_DIST] >= (max_depth-current_depth) and not pv_node:
			if pt_entry[FLAG] == LOWER and pt_entry[VALUE] >= beta:
				return beta
			elif pt_entry[FLAG] == UPPER and pt_entry[VALUE] <= alpha:
				return alpha
			elif pt_entry[FLAG] == EXACT:
				return pt_entry[VALUE]

		# This will be used later in move ordering, its generally good to try the best move we found last time
		# first whenever were searching this position again in the future
		pt_best_move = pt_entry[BEST_MOVE]
		score = pt_entry[VALUE]

	# If we've reached our max depth or the game is over, perform a quiescence search
	# If the game is over, the quiescence search will just immediately return the evaluated board anyway
	if current_depth >= max_depth:
		return quiescence(board, max_depth, max_depth, alpha, beta)
	
	futility_prunable = False

	if not pv_node and not board.is_check() and not game_over:
		# Null move reduction
		if can_null_move and current_depth != 0 and (max_depth-current_depth) >= 3:
			if score is None: score = score_board(board)
			nmp_reduction = int(3 + (max_depth-current_depth) / 3 + min((score - beta)/200, 3)) # some magical math that just works

			if nmp_reduction > 0:
				board.push(chess.Move.null())
				score = alpha_beta(board, current_depth + nmp_reduction, max_depth, -beta, -beta+1, can_null_move=False)
				board.pop()

				if score is None:
					return

				score = -score
				
				if score >= beta and not is_mate_score(score):
					return beta
		
		# futility pruning
		if (max_depth-current_depth) <= FUTILITY_DEPTH:
			if score is None: score = score_board(board)
			if score + FUTILITY_MARGINS[max_depth-current_depth] < alpha:
				futility_prunable = True

		# reverse futility pruning
		if (max_depth-current_depth) <= REVERSE_FUILITY_DEPTH:
			if score is None: score = score_board(board)
			if score - REVERSE_FUTILTIY_MARGINS[max_depth-current_depth] > beta:
				return score

	if game_over:
		score = -CHECKMATE + current_depth if board.is_checkmate() else 0
		if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
			position_table[pt_hash] = (EXACT, max_depth-current_depth, score, None)
		
		return score

	move_count = 0

	# Keep track of the best board we evaluate so we can return it with its full move stack later
	best_move = None
	best_score = -CHECKMATE-1

	# Iterate through all legal moves sorted
	for move in sorted_moves(board.legal_moves, board, current_depth, pt_best_move=pt_best_move):
		move_count += 1

		is_quiet = is_quiet_move(board, move)

		# Futility pruning
		if futility_prunable and is_quiet and not is_mate_score(alpha) and not is_mate_score(beta):
			continue

		# Late move reduction
		reduction = 0
		if move_count >= (LATE_MOVE_REDUCTION_MOVES + int(pv_node) * 2) and is_quiet and not board.is_check() and not board.gives_check(move) and (max_depth-current_depth) >= LATE_MOVE_REDUCTION_LEAF_DISTANCE:
			reduction = LATE_MOVE_REDUCTION_TABLE[min(max_depth-current_depth, LATE_MOVE_REDUCTION_TABLE_SIZE-1)][min(move_count, LATE_MOVE_REDUCTION_TABLE_SIZE-1)]

		# Principal variation search
		board.push(move)

		if game_over:
			score = -CHECKMATE + current_depth if board.is_checkmate() else 0
		else:
			score = alpha_beta(board, current_depth + 1 + reduction, max_depth, -alpha-1, -alpha)
		
		board.pop()

		if score is None:
			return
		
		# This is for negamax, which is a minimax framework where we can just negate the score
		# and bounds for each recursive call and it acts as if weve swapped perspectives
		# (both sides will try to maximize now because the rating will be negated whenever it's blacks turn)	
		score = -score

		if (score > alpha) and (score < beta):
			# Evaluate the move by recursively calling alpha beta
			board.push(move)
			score = alpha_beta(board, current_depth + 1, max_depth, -beta, -alpha)
			board.pop()

			if score is None:
				return

			score = -score

		# Alpha beta pruning cutoff, if weve found the opponent can force a move thats
		# worse for us than they can force in a previous board state we analyzed, then
		# we dont need to evaluate this subtree any further because we know they will
		# always play that move thats worse for us, or something even worse
		if score >= beta:
			if is_quiet:
				# Killer move heuristic
				killer_moves[current_depth].insert(0, move)

				# History heuristic
				history_table[board.turn][move.from_square][move.to_square] += (max_depth-current_depth)**2

				if history_table[board.turn][move.from_square][move.to_square] >= MAX_HISTORY_VALUE:
					shrink_history(history_table)
				
				# Countermove heuristic
				if len(board.move_stack) >= 2:
					countermove_table[board.move_stack[-2].from_square][board.move_stack[-2].to_square] = move

			if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
				position_table[pt_hash] = (LOWER, max_depth-current_depth, beta, move)

			return beta
	
		# Update the lower bound
		if score > best_score:
			best_score = score
			best_move = move

			if score > alpha:
				alpha = score

	# Update the transposition table with the new information we've learned about this position
	if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
		flag = UPPER if alpha <= alpha_orig else EXACT 
		position_table[pt_hash] = (flag, max_depth-current_depth, alpha, best_move)

	return alpha


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
	global seldepth
	nodes += 1

	seldepth = max(seldepth, current_depth)

	# Get the positional evaluation of the current board
	score = score_board(board)

	# We beta cutoff early in quiescence
	if score >= beta:
		return beta

	alpha = max(alpha, score)

	# Filter moves to only be "loud" moves including captures, promotions or checks
	# We only search checks up to a certain depth to avoid searching check repetitions
	# We only really care about tactical checks anyway like forks or discovered checks, etc.
	sorted_quiescence_moves = sorted_moves(
		(move for move in board.legal_moves if not is_quiet_move(board, move, quiescence_depth=current_depth-max_depth)),
		board,
		current_depth
	)

	# Same as the alpha beta negamax search
	for move in sorted_quiescence_moves:
		board.push(move)
		score = quiescence(board, current_depth+1, max_depth, -beta, -alpha)
		board.pop()

		score = -score

		if score >= beta:
			return beta

		alpha = max(alpha, score)

	return alpha

def halted():
	return stop or (allowed_movetime is not None and int((time.time()-search_start_time) * 1000) >= allowed_movetime)

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
	global countermove_table
	global history_table
	global seldepth

	search_start_time = time.time()
	stop = False
	nodes = 0
	depth = STARTING_DEPTH
	bestmove = None

	# Clear the transposition table
	position_table.clear()

	# Fill killer moves cache with None
	killer_moves = [[] for _ in range(MAX_DEPTH)]

	# Setup refutation butterfly table
	countermove_table = [[None for i in range(64)] for j in range(64)]

	# Setup history butterfly table
	history_table = [[[0 for i in range(64)] for j in range(64)] for k in range(2)]

	# This is our first aspiration window guess, before we search depth 1
	gamma = score_board(board)

	# Iterative deepening
	while not halted() and depth < MAX_DEPTH:
		seldepth = 0

		aspw_lower = -ASPIRATION_WINDOW_DEFAULT
		aspw_higher = ASPIRATION_WINDOW_DEFAULT

		if depth >= ASPIRATION_WINDOW_DEPTH:
			while True:
				# We set our bounds to be the size of our aspiration window around our guess (gamma)
				alpha = gamma + aspw_lower
				beta = gamma + aspw_higher

				# Perform the alpha beta search
				score = alpha_beta(board, 0, depth, alpha, beta)

				# If this happens it means we stopped mid search so just end the search
				if score is None:
					break

				# Our next aspiration table guess is the value we gave the board at this depth
				# because we would expect it shouldn't change too much in the next depth	
				gamma = score

				# If we end up outside the aspiration window bounds, we need to make them wider and re search
				if score <= alpha:
					aspw_lower *= ASPIRATION_INCREASE_EXPONENT
				elif score >= beta:
					aspw_higher *= ASPIRATION_INCREASE_EXPONENT
				else:
					# If were inside the bounds, then we can proceed to the next depth
					break
				
		else:
			score = alpha_beta(board, 0, depth, -CHECKMATE, CHECKMATE)
			gamma = score


		# UCI reporting
		if score is not None:
			pv_line = generate_pv_line(board, position_table)
			depth_string = f"depth {depth} seldepth {seldepth}" # full search depth / quiescence search depth
			time_string = f"time {int((time.time()-search_start_time) * 1000)}" # time spent searching this position
			hashfull_string = f"hashfull {int(len(position_table) / MAX_PTABLE_SIZE * 1000)}" # how full the transposition table is
			pv_string = f"pv {' '.join([str(move) for move in pv_line])}" # move preview
			nodes_per_second = int(nodes / (time.time()-search_start_time))

			bestmove = pv_line[0]

			if is_mate_score(score):
				# Checkmate is found, report how many moves its in
				mate_in = math.ceil(len(pv_line) / 2) * COLOR_MOD[score > 0]
				with threading.Lock(): print(f"info nodes {nodes} nps {nodes_per_second} {time_string} {hashfull_string} {depth_string} score mate {mate_in} {pv_string}")
			else:
				# Otherwise just report centipawns score
				with threading.Lock(): print(f"info nodes {nodes} nps {nodes_per_second} {time_string} {hashfull_string} {depth_string} score cp {score} {pv_string}")

		# Prepare for the next search
		depth += 1
	
	if bestmove is None: # if we didn't find a best move in time use move ordering
		bestmove = sorted_moves(list(board.legal_moves), board, 0)[0]
	
	# When we end our search (due to stop command or running out of time), report the best move we found
	with threading.Lock(): print(f"bestmove {bestmove.uci()}")
	
	stop = True


# The board used by UCI commands
board = chess.Board()

# Threads
search_thread = None

if __name__ == "__main__":
	while True:
		# UCI implementation
		line = input()
		args = line.split()
		cmd = args[0] if len(args) else None

		if cmd == "uci":
			with threading.Lock(): print(f"id name {VERSION}")
			with threading.Lock(): print(f"id author {AUTHOR}")
			with threading.Lock(): print("uciok")
		
		elif cmd == "isready":
			with threading.Lock(): print("readyok")
		
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
			elif "wtime" in args and "btime" in args:
				wtime = int(args[args.index("wtime")+1])
				btime = int(args[args.index("btime")+1])

				if "winc" in args and "binc" in args:
					winc = int(args[args.index("winc")+1])
					binc = int(args[args.index("binc")+1])
				else:
					winc = 0
					binc = 0
				
				if board.turn:
					allowed_movetime = max(min(wtime / 40 + winc, max(wtime / 2 - 1000, 0)), 50)
				else:
					allowed_movetime = max(min(btime / 40 + binc, max(btime / 2 - 1000, 0)), 50)

			else:
				allowed_movetime = None
			
			if stop:
				# Begin our search by starting up the threads
				search_thread = threading.Thread(target=lambda: iterative_deepening(board), daemon=True)
				search_thread.start()

		elif cmd == "stop":
			if not stop:
				stop = True
				while search_thread.is_alive():
					pass
