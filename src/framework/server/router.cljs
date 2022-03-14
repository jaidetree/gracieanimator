(ns framework.server.router
  (:require
   [clojure.string :as s]
   [clojure.pprint :refer [pprint]]
   [nbb.core :as nbb]
   [promesa.core :as p]
   [framework.utils :refer [file-exists? url->filepath]]
   ["fs/promises" :as fs]
   ["path" :as path]))


(defn url->cljs-path
  [root url]
  (let [filepath (subs url 1)
        filepath (.replace filepath "/" ".")]
    (str root "." filepath)))

(defn- load-data
  [req loader-fn]
  (if loader-fn
    (p/let [data (loader-fn req (:data req))]
      (update req :data merge data))
    req))

(defn- load-meta
  [req meta-fn]
  (if meta-fn
    (p/let [meta (meta-fn req (:data req))]
      (update req :meta merge meta))
    req))

(defn readdir
  [dirpath]
  (p/->> (fs/readdir dirpath #js {:withFileTypes true})
         (map (fn [dirent]
                (let [filepath (.join path dirpath (.-name dirent))]
                  (cond (.isDirectory dirent)
                        (readdir filepath)

                        (.isFile dirent)
                        [filepath]

                        :else
                        []))
                ))
         (p/all)
         (reduce #(into %1 %2) [])))

(defn normalize-index
  [regex-str]
  (if (= regex-str "$")
    (str "^/$")
    regex-str))

(defn parse-route
  [filepath]
  (let [params (re-seq #"\$[_a-z]+[^_\$\.\/]" filepath)]
    {:file filepath
     :params (->> params
                  (map #(-> (s/replace % #"\$" "")
                            (s/replace #"_" "-")))
                  (map keyword))
     :regex (-> (s/replace filepath #"\$[_a-z]+[^_\$\.\/]" "([^/]+)")
                (s/replace #".*routes" "")
                (s/replace #"\/index" "$")
                (s/replace #"_" "-")
                (s/replace #"\.cljs" "")
                (normalize-index)
                (re-pattern))}))

(defn route-rank
  [{:keys [file regex]}]
  (cond-> 0
    (s/includes? file "$")          (- (* (count (s/split file #"\$")) 100))
    (s/includes? file "index.cljs") (- 10)
    true                            (+ (* (count (s/split file "/")) 1000))))

(defn load-routes
  [root]
  (let [fileroot (.join path "src" (.replace root "." (.-sep path)))]
    (p/->> (readdir fileroot)
           (map parse-route)
           (sort-by route-rank #(compare %2 %1)))))

(defn match-route
  [routes urlpath]
  (->> routes
       (some (fn [route]
               (let [matches (re-find (:regex route) urlpath)]
                 (when matches
                   (merge route
                          {:params (zipmap (:params route) (rest matches))})))))))

(comment
  (p/let [routes (load-routes "gracie.routes")]
    (-> (match-route routes "/storyboards/xyz")
        (pprint)))

  (load-routes "gracie.routes")
  (let [route (parse-route "src/gracie/routes/storyboards/$storyboard_id_$storyboard_slug.cljs")
        {:keys [regex]} route
        results (match-route [route] "/storyboards/abc-xyz")]
    (pprint results)))

(defn load-route-file
  [route]
  (let [ns (-> (:file route)
               (s/replace #"\/" ".")
               (s/replace #"\.cljs", "")
               (subs (inc (s/index-of (:file route) "/")))
               (s/replace #"_" "-"))
        meta-sym (symbol ns "meta")
        loader-sym (symbol ns "loader")
        view-sym   (symbol ns "view")]
    (p/do!
     (nbb/load-file (:file route))
     {:meta (resolve meta-sym)
      :loader (resolve loader-sym)
      :view   (resolve view-sym)})))

(defn route-url
  [routes-path f]
  (p/let [routes (load-routes routes-path)]
    (fn [req]
      (let [target-route (match-route routes (:uri req))]
        (if target-route
          (p/let [{:keys [loader meta view]} (load-route-file target-route)]
            (p/-> req
                  (assoc :params (:params target-route))
                  (load-data loader)
                  (load-meta meta)
                  (f view)))
          (f req))))))

(comment

  (p/let [routes (load-routes "gracie.routes")
          target (match-route routes "/storyboards/category/adult-animation")]
    #_(pprint routes)
    (pprint target))

  (p/let [routes (load-routes "gracie.routes")
          target (match-route routes "/storyboards/MDA1MDYwODMyMjAy/robot-chicken-totoro-sketch-storyboard-artist-stoopid-buddy-adult-animated-comedy")]
    #_(pprint {:routes routes
             :ranks (map route-rank routes)})
    (pprint target))

  )
