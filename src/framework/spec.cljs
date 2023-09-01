(ns framework.spec
  (:refer-clojure :exclude [map or])
  (:require
    [clojure.core :as c]))

(defn map*
  [predicate-map]
  (fn [data]
    (loop [ret {:ok true}
           predicate-map predicate-map]
      (let [[[key pred-spec] & remaining] predicate-map
            {p? :predicate :keys [form]} pred-spec]
        (if (empty? predicate-map)
          ret
          (if (p? (get data key))
            (recur ret remaining)
            {:ok false
             :path [key]
             :context data
             :form form
             :value (get data key)}))))))

(defn spec-runner
  [{:keys [spec-name spec-fn data]}]
  (let [result (spec-fn data)]
    (println result)
    (if (:ok result)
      result
      (throw (js/Error.
               (str
                 "ValidationError: " spec-name " failed: "
                 "At " (:path result) " failed " (:form result)
                 " Received " (:value result)
                 " in " (prn-str (:context result))))))))



(defmacro map
  [predicate-map]
  `(let [predicate-map#
         (into {}
               (list
                 ~@(for [[key predicate-form] predicate-map]
                     `[~key {:predicate ~predicate-form
                             :form (pr-str '~predicate-form)}])))]
     (fn [data]
       (spec-runner
         {:spec-name "map"
          :spec-fn (map* predicate-map#)
          :data data}))))

(defmacro or
  [& predicates]
  ())

(comment
  (map {:a number?})
  ((map {:a number?})
   {:a 1})
  ((map {:a number?})
   {:a :a})

  ((map {:a #(number? %)})
   {:a :a}))
