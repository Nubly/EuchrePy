import numpy as np
from euchre.cards import Card
from euchre.cards import Deck
from euchre.players import Player
# from consolehuman import HumanPlayer
# from basicai import BasicAIPlayer


class StandardGame:
    """Standard game of euchre

    Source: https://en.wikipedia.org/wiki/Euchre
    """

    def __init__(self, team1, team2):
        # Game info
        self.deck = Deck()
        self.team1 = team1
        self.team2 = team2
        self.oppo_team = {team1: team2, team2: team1}
        self.players = [] # List of players, initially equivelant to self.table
        self.table = [] # Ordered players where index 3 is dealer
        self.play_order = [] # Ordered plaeyrs where index 0 is leader
        self.seatPlayers()

        # Trick Info
        self.top_card = None
        self.trump = None
        self.maker = None

    def play(self):
        """Plays a game of euchre until a team reaches 10 points."""
        if len(self.players) != 4:
            raise AssertionError(f"Euchre requires 4 players to play")
        # Game Loop
        while not self.getWinner():
            for p in self.players: p.pointsMsg(self.team1, self.team2)
            for p in self.players: p.dealerMsg(self.table[3])
            maker_selected = self.dealPhase()
            if maker_selected:
                self.playTricks()
            else:
                for p in self.players: p.misdealMsg()
            self.updateTableOrder()

    def dealPhase(self):
        """Deals cards and determines trump.

        Returns:
            (Bool): True if there was a misdeal, False otherwise.
        """
        # Distribute Cards
        self.deck.shuffle()
        hands = self.deck.deal()
        self.kitty = hands[4]
        self.top_card = self.kitty.pop(0)
        for i in range(4):
            self.play_order[i].updateHand(hands[i])
        for p in self.players: p.topCardMsg(self.top_card)

        # Order up and order trump phases
        all_passed = self.orderPhase()
        if all_passed:
            all_passed = self.trumpPhase()

        return not all_passed

    def orderPhase(self):
        """Asks all players if they want to order up the top card.

        Returns:
            (Bool): True if everyone passes ordering up, otherwise False.
        """
        # Ask players if they want to order up top card
        for player in self.table:
            order_up = player.orderUp()
            if order_up:
                self.maker = player
                self.trump = self.top_card.suit
                for p in self.players:
                    p.orderUpMsg(self.maker, self.top_card)
                for p in self.players:
                    p.newTrumpMsg(self.trump)
                discard_card = self.table[3].discardCard(self.top_card)
                self.kitty.append(discard_card)
                return False
            else:
                for p in self.players: p.deniedUpMsg(player)
        return True

    def trumpPhase(self):
        """Asks all players if they want to order trump.

        Returns:
            (Bool): True if everyone passes ordering trump, otherwise False.
        """
        # Ask players if they want to order trump
        for player in self.table:
            order_trump = player.orderTrump()

            # Player orders trump
            if order_trump:
                call = player.callTrump(self.top_card.suit)

                # Require valid trump that isn't top card suit
                while not self.validTrump(call):
                    player.invalidSuitMsg()
                    call = player.callTrump(self.top_card.suit)

                self.maker = player
                self.trump = call
                for p in self.players:
                    p.orderedTrumpMsg(self.maker, self.top_card)
                for p in self.players:
                    p.newTrumpMsg(self.trump)
                return False

            # Player denies trump
            else:
                for p in self.players: p.deniedTrumpMsg(player)
        return True

    def playTricks(self):
        """Plays 5 tricks."""
        # Initialize trick information
        going_alone = self.maker.goAlone()
        cards_played = {} # Maps player to cards played
        tricks_taken = {} # Maps players to tricks taken

        # Skip teammate of player going alone
        if going_alone:
            for player in self.play_order:
                if self.maker.getTeammate() is not player:
                    cards_played[player] = []
                    tricks_taken[player] = 0
        else:
            cards_played = {player: [] for player in self.play_order}
            tricks_taken = {player: 0 for player in self.play_order}

        # Init taker to player left of dealer
        taker = self.table[0]

        # Init list of leaders for each trick
        leader_list = []
        for p in self.players: p.leaderMsg(taker)

        # Play tricks
        for j in range(5):

            # Taker of previous round leads
            leader_list.append(taker)
            self.updatePlayOrder(taker)

            for p in self.players: p.trickStartMsg()

            # Play a trick
            for player in self.play_order:
                if going_alone and self.maker.getTeammate() is player:
                    # Skip teammate of player going alone
                    continue
                card = player.playCard(taker, cards_played, self.trump)
                cards_played[player].append(card)
                for p in self.players: p.playedMsg(player, card)

            # Decide Taker
            trick = {player: cards[j] for player, cards in cards_played.items()}
            led_suit = trick[taker].suit
            taker = max(trick,
                        key=lambda player: trick[player].value(
                            led_suit, self.trump))
            for p in self.players: p.takerMsg(taker)
            tricks_taken[taker] += 1

        # Penalize any players that reneged, otherwise score round normally
        renegers = self.checkForReneges(leader_list, cards_played, going_alone)
        if renegers:
            self.penalize(renegers)
        else:
            self.scoreRound(tricks_taken, going_alone)

    def validTrump(self, suit):
        """Checks if a trump call is valid.

        Args:
            suit (Char): The suit that a player has called.

        Returns:
            (Bool): True if the trump is valid, otherwise False.
        """
        if not suit in ['C', 'S', 'H', 'D']:
            return False
        return suit != self.top_card.suit

    def scoreRound(self, tricks_taken, going_alone):
        """Messages players winner and points won.

        Args:
            tricks_taken (Dict): Tricks taken by team
            going_alone (Bool): Whether the maker went alone
        """
        # Count tricks taken per team
        team_tricks = {self.team1: 0, self.team2: 0}
        for player, taken in tricks_taken.items():
            team_tricks[player.team] += taken
        teaking_team = max(team_tricks, key=team_tricks.get)

        # Figure out points
        points = 1
        if self.maker in teaking_team.getPlayers():
            if going_alone and team_tricks[teaking_team] == 5:
                points = 4
            elif team_tricks[teaking_team] == 5:
                points = 2
        else:
            points = 2

        # Finalize results
        teaking_team.points += points
        for p in self.players:
            p.roundResultsMsg(teaking_team, points, team_tricks[teaking_team])

    def penalize(self, renegers):
        """Penalizes the renegers by giving 2 points to the opposing team.

        Args:
            renegers (List): Players to be penalized
        """
        for player in renegers:
            team = self.oppo_team[player.team]
            team.points += 2

    def checkForReneges(self, leader_list, cards_played, going_alone):
        """Figures out who reneged.

        Args:
            leader_list (List): Players ordered by when they lead the trick
            cards_played (Dict): Maps players to a list of cards played
                The list of cards is ordered by trick
            going_alone (Bol): Whether the maker went alone

        Returns:
            renegers (List) Players that reneged and need to be penalized.
        """
        renegers = []

        # Check each trick
        for j in range(5):
            leader = leader_list[j]
            leadSuit = cards_played[leader][j].getSuit(self.trump)

            # Add player to renengers if invalid card played
            for player in self.table:
                # Skip teammate if going alone
                if going_alone and self.maker.getTeammate() is player:
                    continue
                cards = cards_played[player][j:]
                playable = [card for card in cards if card.getSuit(
                    self.trump) == leadSuit]
                if (len(playable) != 0) and (cards[0] not in playable):
                    #TODO Fix this logic, maybe penalties should be messaged in batches?
                    # This way if a player reneges twice, the player classes will handle
                    # the messages better and not say that a player was penalized points
                    # for each renege, when they were actually only penalized for one
                    for p in self.players: p.penaltyMsg(player, cards[0])
                    renegers.append(player) if player not in renegers else None

        return renegers

    def seatPlayers(self):
        """Seats the players randomly around table (preserving teams).
        """
        self.players = []
        t1 = self.team1.getPlayers()
        t2 = self.team2.getPlayers()

        # Shuffle within each team
        np.random.shuffle(t1)
        np.random.shuffle(t2)

        # Shuffle order of teams
        teams = [t1, t2]
        np.random.shuffle(teams)

        # Team mates must be across from each other
        self.players.append(teams[0][0])
        self.players.append(teams[1][0])
        self.players.append(teams[0][1])
        self.players.append(teams[1][1])

        # Table order is initially just the players in order
        #   where the 0th index is for the dealer
        self.table = self.players.copy()

        # The player left of the dealer (at 3rd index) should start the trick
        #   (be at the 0th index)
        self.play_order = []
        self.play_order = self.players.copy()
        new_leader = self.play_order.pop(0)
        self.play_order.append(new_leader)

    def updatePlayOrder(self, taker):
        """Updates the play order so the taker of the previous trick goes first.

        Args:
            taker (Player): Player that won the previous trick
        """
        while self.play_order[0] is not taker:
            new_leader = self.play_order.pop(0)
            self.play_order.append(new_leader)

    def updateTableOrder(self):
        """Selects the new dealer.

        Rotates the player order so the player to the left of the dealer
        is the new dealer.
        """
        new_dealer = self.table.pop(0)
        self.table.append(new_dealer)

    def getWinner(self):
        """Fetches the winner.

        Returns:
            winner (Player): Player that won, or if there is no winner, None
        TODO
        """
        return None
