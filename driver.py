from players.consoleplayer import HumanPlayer
from players.basicai import BasicAIPlayer
from players.team import Team
from games.standardgame import StandardGame

p1 = HumanPlayer('User')
ai = []
for i in range(3):
    ai.append(BasicAIPlayer('AI' + str(i)))
team1 = Team(p1, ai[0])
team2 = Team(ai[1], ai[2])
game = StandardGame(team1, team2)
game.play()
