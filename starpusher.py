#!/usr/bin/python3

# Star Pusher (a Sokoban clone), by Al Sweigart al@inventwithpython.com
# (Pygame) A puzzle game where you push the stars over their goals.
import heapq
import pickle, bz2
import random, sys, copy, os, pygame
from pygame.locals import *

GAMESTATEFILE = 'starPusherState'
FPS = 30  # frames per second to update the screen
WINWIDTH = 800  # width of the program's window, in pixels
WINHEIGHT = 600  # height in pixels
HALF_WINWIDTH = int(WINWIDTH / 2)
HALF_WINHEIGHT = int(WINHEIGHT / 2)

# The total width and height of each tile in pixels.
TILEWIDTH = 50
TILEHEIGHT = 85
TILEFLOORHEIGHT = 40

KEYDELAY = 300  # keyboard autorepeat parameters
KEYINTERVAL = 80
FRAMERATE = 50  # framerate for player automove

# The percentage of outdoor tiles that have additional
# decoration on them, such as a tree or rock.
OUTSIDE_DECORATION_PCT = 20

BRIGHTBLUE = (0, 170, 255)
WHITE = (255, 255, 255)
BGCOLOR = BRIGHTBLUE
TEXTCOLOR = WHITE

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


def main():
    global FPSCLOCK, DISPLAYSURF, IMAGESDICT, TILEMAPPING, OUTSIDEDECOMAPPING, BASICFONT, PLAYERIMAGES

    # Pygame initialization and basic set up of the global variables.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()

    # Because the Surface object stored in DISPLAYSURF was returned
    # from the pygame.display.set_mode() function, this is the
    # Surface object that is drawn to the actual computer screen
    # when pygame.display.update() is called.
    DISPLAYSURF = pygame.display.set_mode((WINWIDTH, WINHEIGHT), RESIZABLE)
    pygame.display.set_icon(pygame.image.load('starpusher/icon/starpusher.png'))  # change game icon

    pygame.display.set_caption('Star Pusher')
    BASICFONT = pygame.font.Font('freesansbold.ttf', 18)

    # A global dict value that will contain all the Pygame
    # Surface objects returned by pygame.image.load().
    IMAGESDICT = {'uncovered goal': pygame.image.load('starpusher/images/RedSelector.png'),
                  'covered goal': pygame.image.load('starpusher/images/Selector.png'),
                  'star': pygame.image.load('starpusher/images/Star.png'),
                  'wall': pygame.image.load('starpusher/images/Wood_Block_Tall.png'),
                  'inside floor': pygame.image.load('starpusher/images/Plain_Block.png'),
                  'outside floor': pygame.image.load('starpusher/images/Grass_Block.png'),
                  'title': pygame.image.load('starpusher/images/star_title.png'),
                  'solved': pygame.image.load('starpusher/images/star_solved.png'),
                  'princess': pygame.image.load('starpusher/images/princess.png'),
                  'boy': pygame.image.load('starpusher/images/boy.png'),
                  'catgirl': pygame.image.load('starpusher/images/catgirl.png'),
                  'horngirl': pygame.image.load('starpusher/images/horngirl.png'),
                  'pinkgirl': pygame.image.load('starpusher/images/pinkgirl.png'),
                  'rock': pygame.image.load('starpusher/images/Rock.png'),
                  'short tree': pygame.image.load('starpusher/images/Tree_Short.png'),
                  'tall tree': pygame.image.load('starpusher/images/Tree_Tall.png'),
                  'ugly tree': pygame.image.load('starpusher/images/Tree_Ugly.png')}

    # These dict values are global, and map the character that appears
    # in the level file to the Surface object it represents.
    TILEMAPPING = {'#': IMAGESDICT['wall'],
                   'o': IMAGESDICT['inside floor'],
                   ' ': IMAGESDICT['outside floor']}
    OUTSIDEDECOMAPPING = {'1': IMAGESDICT['rock'],
                          '2': IMAGESDICT['short tree'],
                          '3': IMAGESDICT['tall tree'],
                          '4': IMAGESDICT['ugly tree']}

    # PLAYERIMAGES is a list of all possible characters the player can be.
    PLAYERIMAGES = [IMAGESDICT['princess'],
                    IMAGESDICT['boy'],
                    IMAGESDICT['catgirl'],
                    IMAGESDICT['horngirl'],
                    IMAGESDICT['pinkgirl']]

    startScreen()  # show the title screen until the user presses a key
    pygame.key.set_repeat(KEYDELAY, KEYINTERVAL)  # enable keyboard repetition

    # Read in the levels from the text file. See the readLevelsFile() for
    # details on the format of this file and how to make your own levels.
    levels = readLevelsFile('starPusherLevels.txt')

    # load game state
    try:
        with open(GAMESTATEFILE, 'rb') as f:
            oldState = f.read()
        gameStates = pickle.loads(bz2.decompress(oldState))
    except:
        # no (valid) state file: initialize game state, level 0
        oldState = None
        gameStates = {'levelNum': 0,
                      'currentImage': 1,
                      0: initGameState(levels, 0)}

    # The main game loop. This loop runs a single level, when the user
    # finishes that level, the next/previous level is loaded.
    while True:  # main game loop
        # Run the level to actually start playing the game:
        result = runLevel(levels, gameStates)

        if result == 'next':
            # Go to the next level. If there are no more levels, go back to the first one.
            gameStates['levelNum'] = (gameStates['levelNum'] + 1) % len(levels)
        elif result == 'back':
            # Go to the previous level. If there is no previous level, go to the last one.
            gameStates['levelNum'] = (gameStates['levelNum'] - 1) % len(levels)
        elif result == 'reset':
            gameStateObj = gameStates[gameStates['levelNum']]
            # preserve undo and redo stacks as new redo stack (reset as undo of all steps)
            gameStateObj['undoStack'].reverse()
            redoStack = gameStateObj['redoStack'] + gameStateObj['undoStack']
            gameStateObj = initGameState(levels, gameStates['levelNum'])
            gameStateObj['redoStack'] = redoStack
            gameStates[gameStates['levelNum']] = gameStateObj
        elif result == 'quit':
            # save game state if changed
            newState = bz2.compress(pickle.dumps(gameStates))
            if oldState != newState:
                with open(GAMESTATEFILE, 'wb') as f:
                    f.write(newState)
            terminate()

        if not gameStates['levelNum'] in gameStates:  # game state for this level already exists: use existing
            gameStates[gameStates['levelNum']] = initGameState(levels, gameStates['levelNum'])


def runLevel(levels, gameStates):
    levelNum = gameStates['levelNum']
    gameStateObj = gameStates[levelNum]
    levelObj = levels[levelNum]
    mapObj = decorateMap(levelObj['mapObj'], levelObj['startState']['player'])
    mapNeedsRedraw = True  # set to True to call drawMap()
    levelSurf = BASICFONT.render('Level %s of %s' % (levelNum + 1, len(levels)), 1, TEXTCOLOR)
    levelRect = levelSurf.get_rect()

    levelIsComplete = False
    path = None  # steps to go
    showPath = None  # steps to show
    showPathDest = [-1, -1]  # last analyzed destination
    stretchfactor = 1.0  # scale factor if map is bigger than window

    while True:  # main game loop
        # Reset these variables:
        playerMoveTo = []

        for event in pygame.event.get():  # event handling loop
            if event.type == QUIT:
                # Player clicked the "X" at the corner of the window.
                return 'quit'
            elif event.type == VIDEORESIZE:
                updateWin(event.dict['size'])
                mapNeedsRedraw = True
            elif event.type == VIDEOEXPOSE:  # handles window minimising/maximising
                updateWin(DISPLAYSURF.get_size())
                mapNeedsRedraw = True
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                path = findPath(event.pos, mapObj, gameStateObj, stretchfactor)
            elif event.type == MOUSEMOTION:
                tilePos = mouseToTilePosition(mapObj, event.pos, stretchfactor)
                if not isSameVector(*showPathDest, *tilePos):
                    showPathDest = tilePos
                    newShowPath = a_star_search(tilePos, mapObj, gameStateObj)
                    if showPath != newShowPath:
                        showPath = newShowPath
                        mapNeedsRedraw = True

            elif event.type == KEYDOWN:
                # Handle key presses
                if path:
                    path = None  # cancel rest of path

                if event.key == K_LEFT:
                    playerMoveTo = LEFT
                elif event.key == K_RIGHT:
                    playerMoveTo = RIGHT
                elif event.key == K_UP:
                    playerMoveTo = UP
                elif event.key == K_DOWN:
                    playerMoveTo = DOWN
                elif event.key == K_u:  # undo
                    if gameStateObj['undoStack']:
                        move = gameStateObj['undoStack'].pop()
                        applyMove(gameStateObj, move, undo=True)
                        gameStateObj['redoStack'].append(move)
                        levelIsComplete = False  # if level was solved, it is no more
                        showPathDest = [-1, -1]
                        mapNeedsRedraw = True
                elif event.key == K_r:  # redo
                    if gameStateObj['redoStack']:
                        move = gameStateObj['redoStack'].pop()
                        applyMove(gameStateObj, move, undo=False)
                        gameStateObj['undoStack'].append(move)
                        if isLevelFinished(levelObj, gameStateObj):
                            # level is solved, we should show the "Solved!" image.
                            levelIsComplete = True
                        showPathDest = [-1, -1]
                        mapNeedsRedraw = True

                elif event.key == K_PAGEDOWN:
                    return 'next'
                elif event.key == K_PAGEUP:
                    return 'back'

                elif event.key == K_ESCAPE:
                    return 'quit'
                elif event.key == K_BACKSPACE:
                    return 'reset'  # Reset the level.
                elif event.key == K_p:
                    # Change the player image to the next one.
                    gameStates['currentImage'] = (gameStates['currentImage'] + 1) % len(PLAYERIMAGES)
                    mapNeedsRedraw = True

        if not levelIsComplete:
            if path is not None and len(path) > 0:
                step = path.pop()
                playerPos = gameStateObj['player']
                playerMoveTo = step[0] - playerPos[0], step[1] - playerPos[1]
                FPSCLOCK.tick(FRAMERATE)

            if playerMoveTo:
                # If the player pushed a key to move, make the move
                # (if possible) and push any stars that are pushable.
                moved = makeMove(mapObj, gameStateObj, playerMoveTo)
                if moved:
                    mapNeedsRedraw = True
                    showPath = None  # steps to show
                    showPathDest = [-1, -1]  # last analyzed destination

            if isLevelFinished(levelObj, gameStateObj):
                # level is solved, we should show the "Solved!" image.
                levelIsComplete = True

        if mapNeedsRedraw:
            mapNeedsRedraw = False

            mapSurf = drawMap(mapObj, gameStateObj, levelObj['goals'], showPath, gameStates['currentImage'])
            mapSurfRect = mapSurf.get_rect(center=(HALF_WINWIDTH, HALF_WINHEIGHT))

            # scale if map is bigger than window size
            stretchfactor = min(WINWIDTH / mapSurfRect.width,
                                WINHEIGHT / mapSurfRect.height)
            if stretchfactor < 1.0:
                mapSurf = pygame.transform.rotozoom(mapSurf, 0, stretchfactor)
                mapSurfRect = mapSurf.get_rect(center=(HALF_WINWIDTH, HALF_WINHEIGHT))
            else:
                stretchfactor = 1.0

            DISPLAYSURF.fill(BGCOLOR)

            # Draw mapSurf to the DISPLAYSURF Surface object.
            DISPLAYSURF.blit(mapSurf, mapSurfRect)

            # Draw level number
            levelRect.bottomleft = (20, WINHEIGHT - 35)
            DISPLAYSURF.blit(levelSurf, levelRect)

            # Draw step counters
            stepSurfStr = 'Steps: %s, Pushes: %s' % (gameStateObj['stepCounter'], gameStateObj['pushCounter'])
            if len(gameStateObj['redoStack']) > 0:
                stepSurfStr += f" (Redo: {len(gameStateObj['redoStack'])})"
            stepSurf = BASICFONT.render(stepSurfStr, 1, TEXTCOLOR)
            stepRect = stepSurf.get_rect()
            stepRect.bottomleft = (20, WINHEIGHT - 10)
            DISPLAYSURF.blit(stepSurf, stepRect)

            if levelIsComplete:
                # is solved, show the "Solved!" image
                solvedRect = IMAGESDICT['solved'].get_rect()
                solvedRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT)
                DISPLAYSURF.blit(IMAGESDICT['solved'], solvedRect)

            pygame.display.update()  # draw DISPLAYSURF to the screen.

        FPSCLOCK.tick()


def isWall(mapObj, x, y):
    """Returns True if the (x, y) position on
    the map is a wall, otherwise return False."""
    if x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return False  # x and y aren't actually on the map.
    elif mapObj[x][y] in ('#', 'x'):
        return True  # wall is blocking
    return False


def decorateMap(mapObj, startxy):
    """Makes a copy of the given map object and modifies it.
    Here is what is done to it:
        * The outside/inside floor tile distinction is made.
        * Tree/rock decorations are randomly added to the outside tiles.
        * (Walls that are corners are no more turned into corner pieces.)

    Returns the decorated map object."""

    startx, starty = startxy  # Syntactic sugar

    # Copy the map object so we don't modify the original passed
    mapObjCopy = copy.deepcopy(mapObj)

    # Remove the non-wall characters from the map data
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):
            if mapObjCopy[x][y] in ('$', '.', '@', '+', '*'):
                mapObjCopy[x][y] = ' '

    # Flood fill to determine inside/outside floor tiles.
    floodFill(mapObjCopy, startx, starty, ' ', 'o')

    # decorate outside
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):
            if mapObjCopy[x][y] == ' ' and random.randint(0, 99) < OUTSIDE_DECORATION_PCT:
                mapObjCopy[x][y] = random.choice(list(OUTSIDEDECOMAPPING.keys()))

    return mapObjCopy


def isBlocked(mapObj, gameStateObj, x, y):
    """Returns True if the (x, y) position on the map is
    blocked by a wall or star, otherwise return False."""

    if isWall(mapObj, x, y):
        return True

    elif x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return True  # x and y aren't actually on the map.

    elif (x, y) in gameStateObj['stars']:
        return True  # a star is blocking

    return False


def makeMove(mapObj, gameStateObj, playerMoveTo):
    """Given a map and game state object, see if it is possible for the
    player to make the given move. If it is, then change the player's
    position (and the position of any pushed star). If not, do nothing.

    Returns True if the player moved, otherwise False."""

    # Make sure the player can move in the direction they want.
    playerx, playery = gameStateObj['player']

    # This variable is "syntactic sugar". Typing "stars" is more
    # readable than typing "gameStateObj['stars']" in our code.
    stars = gameStateObj['stars']

    # The code for handling each of the directions is so similar aside
    # from adding or subtracting 1 to the x/y coordinates. We can
    # simplify it by using the xOffset and yOffset variables.
    xOffset, yOffset = playerMoveTo
    if xOffset == 0 and yOffset == 0:
        return False

    # See if the player can move in that direction.
    if isWall(mapObj, playerx + xOffset, playery + yOffset):
        return False

    # a move is a list (1..2) of step lists (xold, yold, xnew, ynew, index)
    # index is stars index, -1 for player
    move = []
    if (playerx + xOffset, playery + yOffset) in stars:
        # There is a star in the way, see if the player can push it.
        if not isBlocked(mapObj, gameStateObj, playerx + (xOffset * 2), playery + (yOffset * 2)):
            # Move the star.
            move.append([playerx + xOffset, playery + yOffset,  # old position
                         playerx + 2 * xOffset, playery + 2 * yOffset,  # new position
                         stars.index((playerx + xOffset, playery + yOffset))])
        else:
            return False
    # Move the player
    move.append([playerx, playery,  # old position
                 playerx + xOffset, playery + yOffset,  # new position
                 -1])  # index=-1 for player
    applyMove(gameStateObj, move)
    gameStateObj['undoStack'].append(move)
    gameStateObj['redoStack'].clear()  # new move, no more redo
    return True


def applyMove(gameStateObj, move, undo=False):
    """Apply steps in move to player and star positions in gameObj
        """

    for step in move:
        if undo:
            x, y = step[0], step[1]  # old position
            increment = -1
        else:
            x, y = step[2], step[3]  # new position
            increment = 1
        index = step[4]
        if index == -1:  # player move
            gameStateObj['player'] = (x, y)
            gameStateObj['stepCounter'] += increment
        else:
            gameStateObj['stars'][index] = (x, y)
            gameStateObj['pushCounter'] += increment


def updateWin(size):
    """Update Window Dimensions.
    Returns None."""

    global WINWIDTH, WINHEIGHT, HALF_WINHEIGHT, HALF_WINWIDTH

    (WINWIDTH, WINHEIGHT) = size
    HALF_WINWIDTH = int(WINWIDTH / 2)
    HALF_WINHEIGHT = int(WINHEIGHT / 2)


def drawStartScreen():
    """Draw the start screen (which has the title and instructions)
    Returns None."""

    # Position the title image.
    titleRect = IMAGESDICT['title'].get_rect()
    topCoord = 50  # topCoord tracks where to position the top of the text
    titleRect.top = topCoord
    titleRect.centerx = HALF_WINWIDTH
    topCoord += titleRect.height

    # Unfortunately, Pygame's font & text system only shows one line at
    # a time, so we can't use strings with \n newline characters in them.
    # So we will use a list with each line in it.
    instructionText = ['Push the stars over the marks.',
                       'Arrow keys to move, P to change character.',
                       'U for Undo, R for Redo.',
                       'Backspace to reset level, Esc to quit.',
                       'PgDown for next level, PgUp to go back a level.']

    # Start with drawing a blank color to the entire window:
    DISPLAYSURF.fill(BGCOLOR)

    # Draw the title image to the window:
    DISPLAYSURF.blit(IMAGESDICT['title'], titleRect)

    # Position and draw the text.
    for i in range(len(instructionText)):
        instSurf = BASICFONT.render(instructionText[i], 1, TEXTCOLOR)
        instRect = instSurf.get_rect()
        topCoord += 10  # 10 pixels will go in between each line of text.
        instRect.top = topCoord
        instRect.centerx = HALF_WINWIDTH
        topCoord += instRect.height  # Adjust for the height of the line.
        DISPLAYSURF.blit(instSurf, instRect)


def startScreen():
    """Display the start screen until the player presses a key."""

    redrawNeeded = True
    while True:  # Main loop for the start screen.
        event = pygame.event.wait()
        if event.type == QUIT:
            terminate()
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                terminate()
            return  # user has pressed a key, so return.
        elif event.type == MOUSEBUTTONDOWN:
            return  # user has pressed a mouse button, also return.
        elif event.type == VIDEORESIZE:
            updateWin(event.dict['size'])
            redrawNeeded = True
        elif event.type == VIDEOEXPOSE:  # handles window minimising/maximising
            updateWin(DISPLAYSURF.get_size())
            redrawNeeded = True

        if redrawNeeded:
            redrawNeeded = False
            drawStartScreen()
            pygame.display.update()  # Display the DISPLAYSURF contents to the actual screen.
        FPSCLOCK.tick()


def readLevelsFile(filename):
    assert os.path.exists(filename), 'Cannot find the level file: %s' % filename
    mapFile = open(filename, 'r')
    # Each level must end with a blank line
    content = mapFile.readlines() + ['\r\n']
    mapFile.close()

    levels = []  # Will contain a list of level objects.
    levelNum = 0
    mapTextLines = []  # contains the lines for a single level's map.
    mapObj = []  # the map object made from the data in mapTextLines
    for lineNum in range(len(content)):
        # Process each line that was in the level file.
        line = content[lineNum].rstrip('\r\n')

        if ';' in line:
            # Ignore everything after and including ";" (comments)
            line = line[:line.find(';')]

        if line != '':
            # This line is part of the map.
            mapTextLines.append(line)
        elif line == '' and len(mapTextLines) > 0:
            # A blank line indicates the end of a level's map in the file.
            # Convert the text in mapTextLines into a level object.

            # Find the longest row in the map.
            maxWidth = -1
            for i in range(len(mapTextLines)):
                if len(mapTextLines[i]) > maxWidth:
                    maxWidth = len(mapTextLines[i])
            # Add spaces to the ends of the shorter rows. This
            # ensures the map will be rectangular.
            for i in range(len(mapTextLines)):
                mapTextLines[i] += ' ' * (maxWidth - len(mapTextLines[i]))

            # Convert mapTextLines to a map object, mirroring x and y (landscape screen orientation)
            for x in range(len(mapTextLines[0])):
                mapObj.append([])
            for y in range(len(mapTextLines)):
                for x in range(maxWidth):
                    mapObj[x].append(mapTextLines[y][x])

            # Loop through the spaces in the map and find the @, ., and $
            # characters for the starting game state.
            startx = None  # The x and y for the player's starting position
            starty = None
            goals = []  # list of (x, y) tuples for each goal.
            stars = []  # list of (x, y) for each star's starting position.
            for x in range(maxWidth):
                for y in range(len(mapObj[x])):
                    if mapObj[x][y] in ('@', '+'):
                        # '@' is player, '+' is player & goal
                        startx = x
                        starty = y
                    if mapObj[x][y] in ('.', '+', '*'):
                        # '.' is goal, '*' is star & goal
                        goals.append((x, y))
                    if mapObj[x][y] in ('$', '*'):
                        # '$' is star
                        stars.append((x, y))

            # Basic level design sanity checks:
            assert startx is not None and starty is not None, (
                f'Level {levelNum + 1} (around line {lineNum}) in {filename} '
                f'is missing a "@" or "+" to mark the start point.')
            assert len(goals) > 0, (
                f'Level {levelNum + 1} (around line {lineNum}) in {filename} '
                f'must have at least one goal.')
            assert len(stars) >= len(goals), (
                f'Level {levelNum + 1} (around line {lineNum}) in {filename} '
                f'is impossible to solve. It has {len(goals)} goals but only {len(stars)} stars.')

            # Create level object and starting game state object.
            gameStateObj = {'player': (startx, starty),
                            'stars': stars}
            levelObj = {'width': maxWidth,
                        'height': len(mapObj),
                        'mapObj': mapObj,
                        'goals': goals,
                        'startState': gameStateObj}

            levels.append(levelObj)

            # Reset the variables for reading the next map.
            mapTextLines = []
            mapObj = []
            levelNum += 1
    return levels


def floodFill(mapObj, x, y, oldCharacter, newCharacter):
    """Changes any values matching oldCharacter on the map object to
    newCharacter at the (x, y) position, and does the same for the
    positions to the left, right, down, and up of (x, y), recursively."""

    # In this game, the flood fill algorithm creates the inside/outside
    # floor distinction. This is a "recursive" function.
    # For more info on the Flood Fill algorithm, see:
    #   http://en.wikipedia.org/wiki/Flood_fill
    if mapObj[x][y] == oldCharacter:
        mapObj[x][y] = newCharacter

    if x < len(mapObj) - 1 and mapObj[x + 1][y] == oldCharacter:
        floodFill(mapObj, x + 1, y, oldCharacter, newCharacter)  # call right
    if x > 0 and mapObj[x - 1][y] == oldCharacter:
        floodFill(mapObj, x - 1, y, oldCharacter, newCharacter)  # call left
    if y < len(mapObj[x]) - 1 and mapObj[x][y + 1] == oldCharacter:
        floodFill(mapObj, x, y + 1, oldCharacter, newCharacter)  # call down
    if y > 0 and mapObj[x][y - 1] == oldCharacter:
        floodFill(mapObj, x, y - 1, oldCharacter, newCharacter)  # call up


def drawMap(mapObj, gameStateObj, goals, showPath, currentImage):
    """Draws the map to a Surface object, including the player, stars,
     and an optional path. This function does not call pygame.display.update(),
     nor does it draw the "Level" and "Steps" text in the corner.
    """

    if showPath is None:
        showPath = []

    # mapSurf will be the single Surface object that the tiles are drawn
    # on, so that it is easy to position the entire map on the DISPLAYSURF
    # Surface object. First, the width and height must be calculated.
    mapSurf = pygame.Surface(getMapSize(mapObj))
    mapSurf.fill(BGCOLOR)  # start with a blank color on the surface.

    # Draw the tile sprites onto this surface.
    for x in range(len(mapObj)):
        for y in range(len(mapObj[x])):
            spaceRect = pygame.Rect((x * TILEWIDTH, y * TILEFLOORHEIGHT, TILEWIDTH, TILEHEIGHT))
            if mapObj[x][y] in TILEMAPPING:
                baseTile = TILEMAPPING[mapObj[x][y]]
            elif mapObj[x][y] in OUTSIDEDECOMAPPING:
                baseTile = TILEMAPPING[' ']
            else:
                raise ValueError("unexpected map tile")  # can't happen, just to get rid of warning

            # First draw the base ground/wall tile.
            mapSurf.blit(baseTile, spaceRect)

            if mapObj[x][y] in OUTSIDEDECOMAPPING:
                # Draw any tree/rock decorations that are on this tile.
                mapSurf.blit(OUTSIDEDECOMAPPING[mapObj[x][y]], spaceRect)
            elif (x, y) in gameStateObj['stars']:
                if (x, y) in goals:
                    # A goal AND star are on this space, draw goal first.
                    mapSurf.blit(IMAGESDICT['covered goal'], spaceRect)
                # Then draw the star sprite.
                mapSurf.blit(IMAGESDICT['star'], spaceRect)
            elif (x, y) in goals:
                # Draw a goal without a star on it.
                mapSurf.blit(IMAGESDICT['uncovered goal'], spaceRect)

            if (x, y) in showPath:
                pygame.draw.circle(mapSurf, (150, 150, 150),
                                   (x * TILEWIDTH + TILEWIDTH / 2,
                                    y * TILEFLOORHEIGHT + (TILEHEIGHT - TILEFLOORHEIGHT) / 2 + 5 + TILEFLOORHEIGHT / 2),
                                   TILEFLOORHEIGHT / 3, 2)

            # Last draw the player on the board.
            if (x, y) == gameStateObj['player']:
                # Note: The value "currentImage" refers
                # to a key in "PLAYERIMAGES" which has the
                # specific player image we want to show.
                mapSurf.blit(PLAYERIMAGES[currentImage], spaceRect)

    return mapSurf


def isLevelFinished(levelObj, gameStateObj):
    """Returns True if all the goals have stars in them."""
    for goal in levelObj['goals']:
        if goal not in gameStateObj['stars']:
            # Found a space with a goal but no star on it.
            return False
    return True


def initGameState(levels, currentLevelIndex):
    """Initialize the game state at the start of a new level.
    Returns gameStateObj."""
    gameStateObj = copy.deepcopy(levels[currentLevelIndex]['startState'])
    gameStateObj['stepCounter'] = 0
    gameStateObj['pushCounter'] = 0
    gameStateObj['undoStack'] = []  # both list of move list of step list
    gameStateObj['redoStack'] = []
    return gameStateObj


def findPath(winPos, mapObj, gameStateObj, stretchfactor):
    tilePos = mouseToTilePosition(mapObj, winPos, stretchfactor)
    return a_star_search(tilePos, mapObj, gameStateObj)


def mouseToTilePosition(mapObj, winPos, stretchfactor):
    if 0.0 < stretchfactor < 1.0:  # if map stretched
        # calc virtual mouse position as if it was not stretched
        winPos = (HALF_WINWIDTH + (winPos[0] - HALF_WINWIDTH) / stretchfactor,
                  HALF_WINHEIGHT + (winPos[1] - HALF_WINHEIGHT) / stretchfactor)
    mapWidth, mapHeight = getMapSize(mapObj)
    mapUpperLeft = (HALF_WINWIDTH - mapWidth / 2,
                    HALF_WINHEIGHT - mapHeight / 2 + (TILEHEIGHT - TILEFLOORHEIGHT) / 2 + 5)
    mapPos = (winPos[0] - mapUpperLeft[0], winPos[1] - mapUpperLeft[1])
    return int(mapPos[0] // TILEWIDTH), int(mapPos[1] // TILEFLOORHEIGHT)


def getMapSize(mapObj):
    mapWidth = len(mapObj) * TILEWIDTH
    mapHeight = (len(mapObj[0]) - 1) * TILEFLOORHEIGHT + TILEHEIGHT
    return mapWidth, mapHeight


# from https://www.geeksforgeeks.org/a-search-algorithm/
# Define the Cell class
class Cell:
    def __init__(self):
        self.parent_i = 0  # Parent cell's row index
        self.parent_j = 0  # Parent cell's column index
        self.f = sys.maxsize  # Total cost of the cell (g + h)
        self.g = sys.maxsize  # Cost from start to this cell
        self.h = 0  # Heuristic cost from this cell to destination


# Check if two vectors (2-dim list) are identical
def isSameVector(x1, y1, x2, y2):
    return x1 == x2 and y1 == y2


# Trace the path from source to destination
def trace_path(cell_details, dest):
    path = []
    row = dest[0]
    col = dest[1]

    # Trace the path from destination to source using parent cells
    while not (cell_details[row][col].parent_i == row and cell_details[row][col].parent_j == col):
        path.append((row, col))
        temp_row = cell_details[row][col].parent_i
        temp_col = cell_details[row][col].parent_j
        row = temp_row
        col = temp_col

    # Add the source cell to the path
    path.append((row, col))
    # Reverse the path to get the path from source to destination
    # path.reverse()  # already done by using pop()
    return path


# Implement the A* search algorithm
def a_star_search(dest, mapObj, gameStateObj):
    src = gameStateObj['player']
    mapWidth = len(mapObj)
    mapHeight = (len(mapObj[0]) - 1)

    if (isBlocked(mapObj, gameStateObj, *dest)  # destination tile blocked or invalid
            or isSameVector(*src, *dest)):  # already there
        return None

    # Initialize the closed list (visited cells)
    closed_list = [[False for _ in range(mapHeight)] for _ in range(mapWidth)]
    # Initialize the details of each cell
    cell_details = [[Cell() for _ in range(mapHeight)] for _ in range(mapWidth)]

    # Initialize the start cell details
    i = src[0]
    j = src[1]
    cell_details[i][j].f = 0
    cell_details[i][j].g = 0
    cell_details[i][j].h = 0
    cell_details[i][j].parent_i = i
    cell_details[i][j].parent_j = j

    # Initialize the open list (cells to be visited) with the start cell
    open_list = []
    heapq.heappush(open_list, (0, i, j))

    # Main loop of A* search algorithm
    while len(open_list) > 0:
        # Pop the cell with the smallest f value from the open list
        p = heapq.heappop(open_list)

        # Mark the cell as visited
        i = p[1]
        j = p[2]
        closed_list[i][j] = True

        # For each direction, check the successors
        for direction in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_i = i + direction[0]
            new_j = j + direction[1]

            # If the successor is valid, unblocked, and not visited
            if not isBlocked(mapObj, gameStateObj, new_i, new_j) and not closed_list[new_i][new_j]:
                # If the successor is the destination
                if isSameVector(new_i, new_j, *dest):
                    # Set the parent of the destination cell
                    cell_details[new_i][new_j].parent_i = i
                    cell_details[new_i][new_j].parent_j = j
                    # Trace and print the path from source to destination
                    return trace_path(cell_details, dest)
                else:
                    # Calculate the new f, g, and h values
                    g_new = cell_details[i][j].g + 1  # way to successor so far
                    h_new = abs(new_i - dest[0]) + abs(new_j - dest[1])  # minimum way to dest (no diagonals)
                    f_new = g_new + h_new  # minimum total way

                    # If the cell is not in the open list or the new f value is smaller
                    if cell_details[new_i][new_j].f > f_new:
                        # Add the cell to the open list
                        heapq.heappush(open_list, (f_new, new_i, new_j))
                        # Update the cell details
                        cell_details[new_i][new_j].f = f_new
                        cell_details[new_i][new_j].g = g_new
                        cell_details[new_i][new_j].h = h_new
                        cell_details[new_i][new_j].parent_i = i
                        cell_details[new_i][new_j].parent_j = j

    # If the destination is not found after visiting all cells
    return None


def terminate():
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
