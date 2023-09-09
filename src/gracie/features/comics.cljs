(ns gracie.features.comics
 (:require
  [promesa.core :as p]
  [gracie.data-pipeline :refer [defhook]]
  [framework.assets :refer [fetch-image]]))

(defhook :comics :parse-project
 (fn comics-parse-project
  [original-project]
  {:id               (get original-project :id)
   :slug             (get original-project :slug)
   :title            (get original-project :title)
   :type             (get original-project :type)
   :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
   :published        (= (get-in original-project [:properties :published :checkbox]) true)
   :images           (for [file (get-in original-project [:properties :image :files])]
                       (get-in file [:file :url]))}))

(defhook :comics :queue-requests
 (fn comics-queue-requests
   [project]
   (for [[idx image-url] (map-indexed vector (:images project))]
     {:id image-url
      :fetch #(fetch-image project "comics" image-url
                           :name (str (:slug project) "-page-" (inc idx)))
      :reducer #(update %1 :images conj %2)})))

(defhook :comics :format-project
 (fn comics-format-project
  [{:keys [project responses]}]
  (let [{:keys [images]} responses
        images (vec (sort-by #(-> (re-find #"-(\d+)\.[a-z]+$" %)
                                  (second)
                                  #_(js/Number))
                             images))]
   (-> project
       (assoc :pages     images
              :thumbnail (first images))
       (dissoc :images)))))

(comment
  (vec (sort-by #(-> (re-find #"-(\d+)\.[a-z]+$" %)
                     (second)
                     (js/Number))
                '("52-dumpling-eternal-page-4.png"
                   "52-dumpling-eternal-page-2.png"
                   "52-dumpling-eternal-page-1.png"
                   "52-dumpling-eternal-page-3.png"))))
