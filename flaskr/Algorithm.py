from collections import OrderedDict
from flaskr import LoadInput


class Recommendation:
    """class containing all methods used for recommending"""
    _ratings = (5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0)

    # _ratings = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)

    def __init__(self, user, flag_print_in_console=False, spearman_coefficient=0.5, min_same_rated_movies=5,
                 threshold_number_of_evaluators=3, threshold_number_of_evaluators_global=30,
                 number_to_recommend=5, threshold_rating=3.5):
        # print in console semi-calculations during recommending - pretty much just for debugging
        self.flag_print_in_console = flag_print_in_console
        # cut of users with smaller spearman_coefficient(than this given) as irrelevant
        self.spearman_coefficient = spearman_coefficient
        # minimal amount of movies that rated both main_user and other_user
        self.min_same_rated_movies = min_same_rated_movies
        # minimal amount of users that must have rated specific movie, so the movie can be recommended
        self.threshold_number_of_evaluators = threshold_number_of_evaluators
        # minimal amount of users that must have rated specific movie, so the movie can be recommended when recommending
        # from global best movies (not user specific)
        self.threshold_number_of_evaluators_global = threshold_number_of_evaluators_global
        # maximum amount of movies that are recommended to user (can be less if not enought movies satisfy conditions)
        self.number_to_recommend = number_to_recommend
        # minimal expected rating that movie must have, so it can be recommended
        self.threshold_rating = threshold_rating

        self.main_user = user
        self.io = LoadInput.IOClass()
        # dict(movie_id, tuple(one-title, second-list of genres))
        self.map_movie_name_on_movie_id = OrderedDict()
        self.map_movie_name_on_movie_id = self.io.load_links()
        self.database = self.io.load_database()

    def final_recommendation(self):
        """control flow of recommendation functions, choose which scenario will be executed and return final results"""
        res = self.spearman_similarity()
        closest_neighbours = self.most_similar_users(res)
        movie_list_users_dict = self.movies_to_recommend(closest_neighbours)
        res = self.recommended_movies(movie_list_users_dict, closest_neighbours)

        # if not enough movies to recommend are found, best movies overall will complement up to
        # "self.number_to_recommend" amount
        if len(res) < self.number_to_recommend:
            res.update(self.find_best_rated_movie_overall())

        if len(res) == 0:
            return False
        new_res = {k: res[k] for k in list(res.keys())[:self.number_to_recommend]}

        final_list = []
        for movie, rating in new_res.items():
            print(movie, rating, self.map_movie_name_on_movie_id[movie][0])
            final_list.append([movie, rating, self.map_movie_name_on_movie_id[movie][0]])
        return final_list

    @staticmethod
    def print_users_with_same_movies_rated(result):
        for key, value in result.items():
            print(f"UserId: {key}, number of same rated movies: {value}")

        print(f"\nTotal number of users with at least one same movie rated: {len(result)}")
        print()

    def users_with_same_movies_rated(self):
        """find all users that have rated at least one common """
        # key = user, value = number of same movies rated with main user
        result = {}

        for user in self.database:
            # ignore when user is main_user's Id
            if user == self.main_user:
                continue

            for k in self.database[user]:
                if k in self.database[self.main_user]:
                    if user in result:
                        result[user] += 1
                    else:
                        result[user] = 1

        if self.flag_print_in_console:
            self.print_users_with_same_movies_rated(result)

        # dict(user_id : number_of_same_rated_movies)
        return result

    @staticmethod
    def print_common_rated_movies(main_user_dict, other_user_dict):
        print('Movie id: | main user: | other user:')
        print('------------------------------------')
        for keys in zip(main_user_dict, other_user_dict):
            print("%8s" % (keys[0]), "%10s" % main_user_dict[keys[0]], "%10s" % other_user_dict[keys[0]])

    def common_rated_movies(self, other_user):
        """return two dictionaries with movieId and its rating for main_user and other_user"""
        main_user_dict = OrderedDict()
        other_user_dict = OrderedDict()

        for movie in self.database[other_user]:
            if movie in self.database[self.main_user]:
                main_user_dict[movie] = self.database[self.main_user][movie]
                other_user_dict[movie] = self.database[other_user][movie]

        if self.flag_print_in_console:
            self.print_common_rated_movies(main_user_dict, other_user_dict)

        # dict(movie_id : user_rating_for_that_movie)
        return main_user_dict, other_user_dict

    def rank_x_and_y(self, main_user_dict, other_user_dict):
        """calculate rank vectors x and y for spearman formula"""
        rank_x_dict = main_user_dict.copy()
        rank_y_dict = other_user_dict.copy()

        n_main = 0
        n_other = 0

        # iterate through ratings 5 .. 0 and assign order numbers to each movie (based on its rating)
        for rating in self._ratings:
            rating_main = 0
            rating_othr = 0
            for keys in zip(main_user_dict, other_user_dict):
                if rating == main_user_dict[keys[0]]:
                    rating_main += 1
                if rating == other_user_dict[keys[0]]:
                    rating_othr += 1

            x_value = float(((n_main + 1) + (n_main + rating_main)) / 2)
            y_value = float(((n_other + 1) + (n_other + rating_othr)) / 2)

            n_main += rating_main
            n_other += rating_othr

            for keys in zip(main_user_dict, other_user_dict):
                if rating == main_user_dict[keys[0]]:
                    rank_x_dict[keys[0]] = x_value
                if rating == other_user_dict[keys[0]]:
                    rank_y_dict[keys[0]] = y_value

        if self.flag_print_in_console:
            self.print_common_rated_movies(rank_x_dict, rank_y_dict)

        # dict(user_id : x_or_y_rank_for_this_user)
        return rank_x_dict, rank_y_dict

    def d_squared(self, rank_x_dict, rank_y_dict):
        """calculate d squared vector for spearman formula"""
        d_squared_vector = []

        for (key1, value1), (key2, value2) in zip(rank_x_dict.items(), rank_y_dict.items()):
            d_squared_vector.append((float(value1) - float(value2)) ** 2)

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for index, (key, d_value) in enumerate(zip(rank_x_dict, d_squared_vector)):
                print("%8s" % key, "%10.5f" % d_squared_vector[index])

        # list(d_squared_values)
        return d_squared_vector

    def candidate_neightbours(self, neighbours):
        """choose neighbours with most same movies rated(with some maximum threshold of chosen neighbours), and filter
        out those whole number of same rated movies is very low, so not relevant"""
        # here could be possibly other in future added further optimizations
        new_neighbours = {key: value for key, value in neighbours.items() if value > self.min_same_rated_movies}
        return new_neighbours

    def spearman_similarity(self):
        """finds spearman sim. between two users that have at least some same rated movies, where first user is main
        user and second is iterated from neighbours"""
        spearman_result = OrderedDict()
        # get all users that have at least "self.min_same_rated_movies"
        neighbours = self.users_with_same_movies_rated()
        neighbours = self.candidate_neightbours(neighbours)

        for key, value in neighbours.items():
            main_user_dict, other_user_dict = self.common_rated_movies(key)
            rank_x_dict, rank_y_dict = self.rank_x_and_y(main_user_dict, other_user_dict)

            d_squared_vector = self.d_squared(rank_x_dict, rank_y_dict)
            current_n = len(rank_x_dict)

            # spearman formula
            p = 1 - ((6 * sum(d_squared_vector)) / (current_n * ((current_n ** 2) - 1)))
            spearman_result[key] = p

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for key, value in spearman_result.items():
                print("%8s" % key, "%10.5f" % value)

        return spearman_result

    def most_similar_users(self, user_spearman_dict):
        """finds most similar users based on results from spearman_similarity() and cut of irrelevant users
         on threshold"""

        closest_neighbours = {key: value for key, value in user_spearman_dict.items()
                              if value > self.spearman_coefficient}
        # currently not used, but can be used for further optimizations
        # distant_neighbours = {key: value for key, value in user_spearman_dict.items()
        #                       if value < (-1 * self.spearman_coefficient)}

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for key, value in closest_neighbours.items():
                print("%8s" % key, "%10.5f" % value)

        # dict(user : his relevance to main user)
        return closest_neighbours

    def movies_to_recommend(self, closest_neighbours):
        """find all users """

        quantity_dict = OrderedDict()
        movie_list_users_dict = {}

        for user in closest_neighbours:
            for movie in self.database[user]:
                if movie in quantity_dict:
                    quantity_dict[movie] += 1
                    movie_list_users_dict[movie].append(user)
                else:
                    quantity_dict[movie] = 1
                    movie_list_users_dict[movie] = [user]

        for movie in self.database[self.main_user]:
            quantity_dict.pop(movie, None)

        movie_list_users_dict = {key: value for key, value in movie_list_users_dict.items()
                                 if len(value) > self.threshold_number_of_evaluators}

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for key, value in closest_neighbours.items():
                print("%8s" % key, "%10.5f" % value)

        return movie_list_users_dict

    def recommended_movies(self, movie_list_users_dict, closest_neighbours):
        """calculating what movie to recommend by averaging rating of neighbours weighted by their similarity to
                main user"""
        movie_to_recommend_dict = OrderedDict()

        for movie, users in movie_list_users_dict.items():
            weighted_denominator = 0
            coefficient = 0
            for user in users:
                coefficient += self.database[user][movie] * closest_neighbours[user]
                weighted_denominator += closest_neighbours[user]

            coefficient = coefficient / weighted_denominator
            movie_to_recommend_dict[movie] = coefficient

        movie_to_recommend_dict = {key: value for key, value in movie_to_recommend_dict.items()
                                   if value > self.threshold_rating}
        movie_to_recommend_dict = OrderedDict(sorted(movie_to_recommend_dict.items(), key=lambda x: x[1], reverse=True))

        if self.flag_print_in_console:
            for movie, coefficient in movie_to_recommend_dict.items():
                print("Movie: %8s" % movie, "coefficient: %8.5f" % coefficient,
                      "quantity: %3s" % len(movie_list_users_dict[movie]))

        # dict(movie_id : correlation_value)
        return movie_to_recommend_dict

    def find_best_rated_movie_overall(self):
        result_dict = OrderedDict()
        for _, value in self.database.items():
            for movie, rating in value.items():
                if movie in result_dict:
                    result_dict[movie][0] += rating
                    result_dict[movie][1] += 1
                else:
                    result_dict[movie] = [rating, 1]

        result_dict = {key: value for key, value in result_dict.items()
                       if value[1] > self.threshold_number_of_evaluators_global}

        final_result_dict = OrderedDict()
        for key, value in result_dict.items():
            final_result_dict[key] = value[0] / value[1]

        final_result_dict = {key: value for key, value in final_result_dict.items()
                             if value > self.threshold_rating}

        final_result_dict = OrderedDict(sorted(final_result_dict.items(), key=lambda x: x[1], reverse=True))

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for key, value in final_result_dict.items():
                print("%8s" % key, "%10.5f" % value)

        # dict(movie_id : rating)
        return final_result_dict

    def main_user_ratings(self):
        """return user's movies that he rated, their rating and Id"""
        user_ratings = []
        for movie, rating in self.database[self.main_user].items():
            print(movie, rating, self.map_movie_name_on_movie_id[movie][0])
            user_ratings.append([movie, rating, self.map_movie_name_on_movie_id[movie][0]])

        # return list(list()), where in inner lists are 0 movieId, 1 movieRating, 2 movieName
        return user_ratings

    def all_movies(self):
        """return all movies and their Id's"""
        res_dict = OrderedDict()
        for key, value in self.map_movie_name_on_movie_id.items():
            res_dict[key] = value[0]

        if self.flag_print_in_console:
            print('Movie id: | main user: ')
            print('-----------------------')
            for key, value in res_dict.items():
                print("%8s" % key, "%10.5f" % value)

        # dict(movie_id : movie_name)
        return res_dict

    def change_database(self, movie_id, new_rating):
        movie_id = str(movie_id)
        if movie_id not in self.map_movie_name_on_movie_id.keys() or new_rating > 5 or new_rating < 0:
            return False
        # movie_id = int(movie_id)
        if self.main_user in self.database:
            if movie_id in self.database[self.main_user]:
                self.database[self.main_user][movie_id] = new_rating
                self.io.update_rating(self.main_user, movie_id, new_rating)
            else:
                self.database[self.main_user][movie_id] = new_rating
                self.io.add_new_rating(self.main_user, movie_id, new_rating)
        else:
            self.database[self.main_user] = {movie_id: new_rating}
            self.io.add_new_rating(self.main_user, movie_id, new_rating)
        return True
