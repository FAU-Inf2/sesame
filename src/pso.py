from math import tanh
import random
import time

def sign(x):
    if x == 0:
        return 0
    if x > 0:
        return 1
    return -1


class Particle:
    def __init__(self, position, velocity):
        self.__position = position
        self.__velocity = velocity
        self.__bestpos = list(position)

    def _getpos(self):
        return self.__position

    def _getvel(self):
        return self.__velocity

    def _getbestpos(self):
        return self.__bestpos

    def _setbestpos(self):
        self.__bestpos = list(self.__position)

    def _update(self, damping, localfactor, globalfactor, globalbest, low, high):
        for i in range(0, len(self.__velocity)):
            self.__velocity[i] = damping * (self.__velocity[i] +
                localfactor * random.uniform(0, 1) * (self.__bestpos[i] - self.__position[i]) +
                globalfactor * random.uniform(0, 1) * (globalbest[i] - self.__position[i]))
            self.__position[i] = self.__position[i] + self.__velocity[i]



class ParticleSwarmOptimizer:
    def __init__(self, quality, terminate, low, high, damping, localfactor, globalfactor, bestselector):
        self.__quality = quality
        self.__terminate = terminate
        self.__low = low
        self.__high = high
        self.__damping = damping
        self.__localfactor = localfactor
        self.__globalfactor = globalfactor
        self.__bestselector = bestselector


    def __random(self, low, high):
        assert len(low) == len(high)
        result = Particle([ random.uniform(low[i], high[i]) for i in range(len(low)) ],
            [ random.triangular(-2 * abs(high[i] - low[i]), 2 * abs(high[i] - low[i]))
                for i in range(len(low)) ])
        # Move a random component to the boundary of the search space
        compn = random.randrange(len(low))
        if random.choice((True, False)):
            result._getpos()[compn] = low[compn]
            result._getvel()[compn] = abs(result._getvel()[compn])
        else:
            result._getpos()[compn] = high[compn]
            result._getvel()[compn] = -abs(result._getvel()[compn])
        return result


    def _eval_quality(self, pos):
        if any( pos[i] < self.__low[i] or pos[i] > self.__high[i] for i in range(len(pos)) ):
            return float("-inf")
        return self.__quality(pos)


    def optimize(self, n):
        if isinstance(n, int):
            return self._optimize([ self.__random(self.__low, self.__high) for i in range(0, n) ])
        return self._optimize([ Particle(pos, 
            [ random.triangular(-2 * abs(self.__high[i] - self.__low[i]),
                    2 * abs(self.__high[i] - self.__low[i]))
                for i in range(0, len(self.__low)) ])
            for pos in n ])

    def _optimize(self, particles):
        best = self.__bestselector(particles, self._eval_quality)
        while not self.__terminate(best.result(), self._eval_quality(best.result())):
            start = time.time()
            i = 0
            for p in particles:
                p._update(self.__damping, self.__localfactor, self.__globalfactor, best.bestfor(p), self.__low, self.__high)
                if best.isimprovement(p):
                    p._setbestpos()
                    best.update(p)
            end = time.time()
            print("iteration took " + str(end - start) + " s ; best: " + str(self._eval_quality(best.result())))
            best.nextiter()
        print("best = " + str(best.result()))
        return best.result()



class ParticleSwarmAdapter:
    def __init__(self, cls, features, quality, terminate, damping, localfactor, globalfactor, bestselector):
        self.__init_features(features)
        self.__opt = cls(self.__qadapt, terminate, self.__low, self.__high,
            damping, localfactor, globalfactor, bestselector)
        self.__quality = quality


    def __init_features(self, features):
        self.__ftov = dict()
        self.__vtof = dict()
        self.__low = list()
        self.__high = list()
        for i in range(0, len(features)):
            vv = 0
            for fv in features[i]:
                assert (i, fv) not in self.__ftov
                self.__ftov[(i, fv)] = vv
                self.__vtof[(i, vv)] = fv
                vv += 1
            self.__low.append(-0.5)
            self.__high.append(vv - 0.5)


    def __getf(self, v, i):
        return self.__vtof[min(filter(lambda x: i == x[0], self.__vtof.keys()), key=lambda x: abs(x[1] - v))]


    def __qadapt(self, vec):
        return self.__quality([ self.__getf(vec[i], i) for i in range(0, len(vec)) ])


    def optimize(self, n):
        vec = self.__opt.optimize(n)
        return [ self.__getf(vec[i], i) for i in range(0, len(vec)) ]



class FixedIterationTerminator:
    def __init__(self, n):
        self.__i = 0
        self.__n = n

    def __call__(self, best, bestq):
        self.__i += 1
        return self.__i > self.__n


class NoBestChangeForNIterations:
    def __init__(self, n):
        self.__n = n
        self.__i = 0
        self.__best = None

    def __call__(self, best, bestq):
        if self.__best == best:
            self.__i += 1
            return self.__i > self.__n
        else:
            self.__best = best
            self.__i = 0
            return False


class FixedQualityReached:
    def __init__(self, q):
        self.__q = q

    def __call__(self, best, bestq):
        return bestq >= self.__q


class OrTermination:
    def __init__(self, *ts):
        self.__ts = ts

    def __call__(self, best, bestq):
        return any( t(best, bestq) for t in self.__ts )


class GlobalBestPosition:
    def __init__(self, particles, qf):
        self.__qf = qf
        start2 = time.time()
        self.__best = list(max(map(lambda x: x._getpos(), particles), key=self.__qf))
        end2 = time.time()
        print("selecting best took " + str(end2 - start2) + " s (" + str(self.__qf(self.__best)) + ")")

    def _qf(self):
        return self.__qf

    def update(self, p):
        if self.__qf(p._getpos()) > self.__qf(self.__best):
            self.__best = list(p._getpos())

    def bestfor(self, p):
        return self.result()

    def isimprovement(self, p):
        return self.__qf(p._getpos()) > self.__qf(p._getbestpos())

    def nextiter(self):
        pass

    def result(self):
        return self.__best


class RingTopologyBestPosition(GlobalBestPosition):
    def __init__(self, particles, qf):
        GlobalBestPosition.__init__(self, particles, qf)
        part_list = list(particles)
        for i in range(0, len(part_list)):
            part_list[i].__dict__["_pso_RTBP_left_neigh"] = part_list[(i - 1) % len(part_list)]
            part_list[i].__dict__["_pso_RTBP_right_neigh"] = part_list[(i + 1) % len(part_list)]

    def bestfor(self, p):
        return max([p, p.__dict__["_pso_RTBP_left_neigh"], p.__dict__["_pso_RTBP_right_neigh"]],
            key=lambda x: self._qf()(x._getbestpos()))._getbestpos()


class StretchingAdapterBuilder:
    def __init__(self, delegate, gamma1 = 10000, gamma2 = 1, mu = 1e-9):
        self.__delegate = delegate
        self.__gamma1 = gamma1
        self.__gamma2 = gamma2
        self.__mu = mu

    def __call__(self, particles, qf):
        return StretchingAdapter(particles, qf, self.__delegate, self.__gamma1, self.__gamma2, self.__mu)


class StretchingAdapter:
    def __init__(self, particles, qf, delegate, gamma1, gamma2, mu):
        self.__delegate = delegate(particles, qf)
        self.__origqf = qf
        self.__curqf = qf
        self.__gamma1 = gamma1
        self.__gamma2 = gamma2
        self.__mu = mu
        self.__lastq = float("-inf")
        self.__nochange = 0

    def _qf(self):
        return self.__curqf

    def update(self, p):
        self.__delegate.update(p)

    def bestfor(self, p):
        return self.__delegate.bestfor(p)

    def isimprovement(self, p):
        return self.__curqf(p._getpos()) > self.__curqf(p._getbestpos())

    def nextiter(self):
        mnx = self.result()
        curq = self.__origqf(mnx)
        if curq == self.__lastq:
            if self.__nochange == 5: # No change for 5 iterations:
                # Apply function stretching
                oldf = self.__curqf
                g = lambda x, oldf=oldf, mn=mnx: oldf(x) - self.__gamma1 * (sum(map(lambda p: p[0] - p[1], zip(x, mnx))) * (sign(oldf(mn) - oldf(x)) + 1)) / 2.0
                self.__curqf = lambda x, oldf=oldf, mn=mnx, g=g: g(x) - self.__gamma2 * (sign(oldf(x) - oldf(mn)) + 1) / (2 * tanh(self.__mu * (g(mn) - g(x))) + 1e-10)
            self.__nochange += 1
        else:
            self.__nochange = 0
        self.__lastq = curq

    def result(self):
        return self.__delegate.result()


class CacheQuality:
    def __init__(self, fun):
        self.__cache = dict()
        self.__fun = fun

    def __call__(self, arg):
        tp = tuple(arg)
        if tp in self.__cache:
            return self.__cache[tp]
        #try:
        v = self.__fun(arg)
        #except ValueError:
        #    v = float("-inf")
        self.__cache[tp] = v
        return v
